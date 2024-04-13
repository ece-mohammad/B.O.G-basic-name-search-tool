#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Provides a base class for site searching websites for martyred children."""

import abc
import asyncio
import json
import logging as log
import pathlib
import random
import re
from collections import namedtuple
from itertools import chain
from typing import Dict, Final, List
from urllib import parse

import aiohttp
from anyio import open_file
from bs4 import BeautifulSoup

Logger: Final[log.Logger] = log.getLogger(__name__)
AgentsFile: Final[pathlib.Path] = pathlib.Path(__file__).parent / "agents.json"
FetchResult = namedtuple("FetchResult", ["url", "status", "html"])


class SearchResult:
    """A Wrapper class for search results.

    Attributes:
        - url: The url of the search result
        - name: The name used in the search query
        - instances: The instances of the name in the url's page

    Methods:
        - to_dict: Convert search result instance into a nested dictionary
        - from_dict: Update search result instance from a dictionary
    """

    def __init__(self, url: str, name: str, instances: List[str] | None):
        self.url: str = url
        self.name: str = name
        self.instances: List[str] | None = instances[:] if instances else None

    def to_dict(self) -> Dict[str, Dict[str, List[str]]]:
        """Convert search result instance into a nested dictionary.

        :return: A dictionary that contains the name as a key, and a nested
        dictionary that contains the search query as a key, and a list of
        instances as a value. For example:
        "name": {
            "query url": ["name instance 1", "name instance 2"]
        }
        """
        return {
            self.name: {
                self.url: self.instances[:] if self.instances else None
            }
        }

    def from_dict(self, data: Dict[str, Dict[str, List[str]]]) -> None:
        """Update search result instance from a dictionary.

        :param data: A dictionary that contains the name as a key, and a nested
        dictionary that contains the search query as a key, and a list of
        instances as a value. For example:
        "name": {
            "query url": ["name instance 1", "name instance 2"]
        }
        :type data: Dict[str, Dict[str, List[str]]]
        """
        self.name = list(data.keys())[0]
        self.url = list(data[self.name].keys())[0]
        self.instances = data[self.name][self.url][:]

    def __str__(self):
        return f"{self.url}:{self.name}:{self.instances}"


class BaseFetch(abc.ABC):
    """An abstract base class for fetching web pages.

    Subclasses must implement the fetch_page() method, and
    async_setch_page() method.
    """

    @abc.abstractmethod
    async def fetch_setup(self, *args, **kwargs):
        """Sets up objects required to fetch web pages."""
        ...

    @abc.abstractmethod
    async def fetch_teardown(self, *args, **kwargs):
        """Closes/deletes objects that were used to fetch web pages."""
        ...

    @abc.abstractmethod
    async def fetch_page(self, page_url: str, **kwargs) -> FetchResult:
        """Get the contents of a web page

        :param page_url: url of the page
        :type page_url: str
        :return: A FetchResult instance that contains the url, the status code
        and the page's content.
        :rtype: FetchResult
        """
        ...


class StaticFetch(BaseFetch):
    """A class that fetches web pages from a static site."""

    async def fetch_setup(self, *args, **kwargs):
        """Create a new aiohttp.ClientSession and set the User-Agent header."""
        async with await open_file(AgentsFile) as f:
            contents: str = await f.read()
        agents: List[Dict[str, str]] = json.loads(contents)
        self.user_agent: str = random.choice(agents)["ua"]
        self.headers: Dict[str, str] = {"User-Agent": self.user_agent}
        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            headers=self.headers
        )
        Logger.debug(f"Using headers: {self.user_agent}")

    async def fetch_teardown(self, *args, **kwargs):
        """Close the aiohttp.ClientSession session."""
        await self.session.close()

    async def fetch_page(self, page_url: str, **kwargs) -> FetchResult:
        """Get the contents of a web page

        :param page_url: url of the page
        :type page_url: str
        :return: A FetchResult instance that contains the url, the status code
        and the page's content.
        :rtype: FetchResult
        """
        Logger.debug(f"Fetching page: {page_url}")
        async with self.session.get(page_url) as response:
            if response.status != 200:
                html = None
                Logger.error(
                    f"Error: {response.status} while fetching page: {page_url}"
                )
            else:
                html = await response.text(encoding="utf-8")
        return FetchResult(page_url, response.status, html)


class BaseSite(abc.ABC):
    """An abstract base class for a site that is searched for martyrs' names.

    The class is abstract and cannot be instantiated. Subclasses must
    implement the `search_name` method.

    Class Attributes:
        - Name: The name of the site
        - HomePage: The home page of the site

    Methods:
        - fetch_page: Get the contents of a web page
        - search_name: Searches the website for martyr name
        - search_names: Searches the website for multiple martyrs' names
    """

    Name: str = ""
    HomePage: str = ""

    @staticmethod
    def grep_html(html: str, text: str) -> List[str]:
        """Search the html of a web page for a text"""
        matches: List[str] = []
        parsed_html = BeautifulSoup(html, "html.parser")
        body = parsed_html.body
        for line in body.text.split("\n"):
            if re.search(f"\\b{text}\\b", line, re.IGNORECASE):
                matches.append(line.strip())
        return matches

    @abc.abstractmethod
    async def search_setup(self) -> None:
        """Setup any objects required for searching the site.
        It's called in object's __init__, and should add objects
        as attributes to the class. The attributes can be used by other
        methods in the class. For example:
        - setting up aiohttp.ClientSession as an attribute so that it
        can be used in the search_name, instead of creating a new
        session for each call of search_name.

        :return: None
        """
        ...

    @abc.abstractmethod
    async def search_teardown(self) -> None:
        """Teardown any objects that were added to the class.

        It should close/terminate any objects started/initialized in setup. The
        method is called in search_names, after the search is completed.

        :return: None
        """
        ...

    @abc.abstractmethod
    async def search_name(
        self, martyr_name: str, **kwargs
    ) -> List[SearchResult]:
        """Searches the website for martyr name.

        Do not use this method to search for names, use search_names instead.
        search_names() method uses this method to search for multiple
        names in the site. This method must be implemented by subclasses.
        It shouldn't call search_setup() or search_teardown(), they are called
        in search_names() method.

        :param martyr_name: name to search for in thr site
        :type martyr_name: str
        :return: A list of SearchResult instances that contains the name, the
        search query and the instances where the name was mentioned
        :rtype: List[SearchResult]
        """
        ...

    async def search_names(
        self, martyr_names: List[str]
    ) -> List[SearchResult]:
        """Searches the site for martyrs by name.

        It uses the class's implementation of search_name() method to search
        for multiple names in the site. It calls search_setup() once before
        searching, and search_teardown() after search is complete.

        :param martyr_names: names to search for in the site
        :type martyr_names: List[str]
        :return: A list of SearchResult instances that contains the name, the
        search query and the instances where the name was mentioned
        :rtype: List[SearchInstance]
        """
        Logger.info(
            f"Searching site: {self.Name} for names: {', '.join(martyr_names)}"
        )
        await self.search_setup()
        tasks = [self.search_name(name) for name in martyr_names]
        results: List[List[SearchResult]] = await asyncio.gather(*tasks)
        await self.search_teardown()
        return list(chain(*results))


class SinglePageSite(StaticFetch, BaseSite):
    """A Basic site where the data is located in a single pages, and the search
    query isn't related to the search term.

    SinglePageSite subclasses BaseSite and implements the `search_name()`
    method to search for names in the html of the site's page. The response
    of the URL is searched for the name using Regex. The search is
    case-insensitive. The results contain the lines in the response that
    contain the name. The results may contain duplicates.

    Class Attributes:
        - URLS: A list of URLs where the data is located.
    """

    URLS: List[str] = ""

    def __init__(self):
        self.html: List[FetchResult] = []

    async def search_setup(self):
        await self.fetch_setup()
        self.html: List[FetchResult] = await asyncio.gather(
            *[self.fetch_page(url) for url in self.URLS]
        )

    async def search_teardown(self):
        await self.fetch_teardown()

    async def search_name(
        self, martyr_name: str, **kwargs
    ) -> List[SearchResult]:
        search_results: List[SearchResult] = []
        for page in self.html:
            if page.html is None:
                break

            matches = self.grep_html(page.html, martyr_name)
            if matches:
                search_results.append(
                    SearchResult(page.url, martyr_name, matches)
                )
                Logger.debug(
                    f"Found {len(matches)} matches in {self.Name} for {martyr_name}"
                )
            else:
                Logger.debug(
                    f"Found no matches in {self.Name} for {martyr_name}"
                )

        return search_results


class SinglePageQuerySite(StaticFetch, BaseSite):
    """A Basic site where the response of a query URL is searched for names.

    SinglePageQuerySite subclasses BaseSite and implements the search_name method
    to search for names in the response of a query URL. First, the query URL
    is constructed by replacing the {name} placeholder in the QueryTemplate
    with the name to search for. Then, the response of the query URL is
    searched for the name using Regex. The search is case-insensitive.
    The results contain the lines in the response that contain the name.
    The results may contain duplicates.

    Class Attributes:
        - QueryTemplates: The query templates for the site used to search for
        names. Query templates must contain the {name} placeholder.
    """

    QueryTemplates: List[str] = ""

    async def search_setup(self):
        await self.fetch_setup()

    async def search_teardown(self):
        await self.fetch_teardown()

    async def search_name(
        self, martyr_name: str, **kwargs
    ) -> List[SearchResult]:
        Logger.debug(f"Searching site: {self.Name} for name {martyr_name}...")
        queries = [
            q.format(name=parse.quote_plus(martyr_name))
            for q in self.QueryTemplates
        ]
        Logger.debug(f"Queries: {queries}")

        tasks = [self.fetch_page(query) for query in queries]
        pages: List[FetchResult] = await asyncio.gather(*tasks)
        search_results: List[SearchResult] = []
        for page in pages:
            if page.html is None:
                continue

            if page.status != 200:
                continue

            matches: List[str] = self.grep_html(page.html, martyr_name)
            if matches:
                search_results.append(
                    SearchResult(page.url, martyr_name, matches)
                )
                Logger.debug(f"Found {len(matches)} match(es) in {page.url}")
            else:
                Logger.debug(f"No matches for {martyr_name} in {page.url}")
        return search_results


class PaginatedSite(StaticFetch, BaseSite):
    """A Subclass of BaseSite for sites that have pagination.

    Like SingePageSite, the search query is not related to the search term. But
    the data is located in multiple pages. Pages are cycled through until the
    response is not found (response status is not 200).

    Class Attributes:
        - UrlTemplate: The URL template for the site. The URL template must
        contain the {page} placeholder.
        - FirstPage: The first page of the site. The default value, as in most
        cases, is 1. But some sites don't use pagination index for the first
        page, in that case, it should be set to 0.
    """

    UrlTemplate: str = ""
    FirstPage: int = 1

    async def search_setup(self) -> None:
        await super().fetch_setup()
        self.page_index: int = self.FirstPage

    async def search_teardown(self) -> None:
        await self.fetch_teardown()

    async def search_name(
        self, martyr_name: str, **kwargs
    ) -> List[SearchResult]:
        Logger.debug(f"Searching for name {martyr_name} in {self.Name}...")
        page = kwargs["page"]
        search_results: List[SearchResult] = []
        if page.html:
            matches: List[str] = self.grep_html(page.html, martyr_name)
            if matches:
                search_results.append(
                    SearchResult(page.url, martyr_name, matches)
                )
                Logger.debug(f"Found {len(matches)} match(es) in {page.url}")
            else:
                Logger.debug(
                    f"Found no matches for {martyr_name} in {page.url}"
                )
        return search_results

    async def get_pages(self) -> List[FetchResult]:
        pages: List[FetchResult] = []
        iter_pages: bool = True
        while iter_pages:
            if self.page_index == 0:
                pages.append(
                    await self.fetch_page(self.UrlTemplate.format(page=""))
                )
                self.page_index = 2
            else:
                pages.extend(
                    await asyncio.gather(
                        *[
                            self.fetch_page(self.UrlTemplate.format(page=page))
                            for page in range(
                                self.page_index, self.page_index + 5
                            )
                        ]
                    )
                )
                self.page_index += 5

            for page in pages:
                if page.status == 404:
                    iter_pages = False
                    break

        return pages

    async def search_names(
        self, martyr_names: List[str]
    ) -> List[SearchResult]:
        Logger.info(
            f"Searching site: {self.Name} for names: {', '.join(martyr_names)}"
        )
        await self.search_setup()

        pages: List[FetchResult] = await self.get_pages()
        tasks = [
            self.search_name(name, page=page)
            for name in martyr_names
            for page in pages
        ]
        results: List[List[SearchResult]] = await asyncio.gather(*tasks)

        await self.search_teardown()
        return list(chain(*results))


class PaginatedQuerySite(StaticFetch, BaseSite):
    """A Subclass of SinglePageQuerySite for sites that have pagination.

    Pages are cycled through until the response is not found (RC 404). The
    QueryTemplate must contain the {page} placeholder, in addition to the
    {name} placeholder.

    Class Attributes:
        - UrlTemplate: The URL template for the site. The URL template must
        contain the {page} placeholder, as well as the {name} placeholder.
        - FirstPage: The first page of the site. The default value, as in most
        cases, is 1. But some sites don't use pagination index for the first
        page, in that case, it should be set to 0.
    """

    QueryTemplate: str = ""
    StartPage: int = 1

    async def search_setup(self):
        await super().fetch_setup()
        self.page = 1

    async def search_teardown(self) -> None:
        await self.fetch_teardown()

    async def search_name(
        self, martyr_name: str, **kwargs
    ) -> List[SearchResult]:
        Logger.debug(f"Searching for name {martyr_name} in {self.Name}...")
        results: List[SearchResult] = []

        request_pages: bool = True
        while request_pages:
            tasks = [
                self.fetch_page(
                    self.QueryTemplate.format(
                        name=parse.quote_plus(martyr_name),
                        page=page
                    )
                )
                for page in range(self.page, self.page + 5)
            ]
            self.page += 5
            responses = await asyncio.gather(*tasks)
            for response in responses:
                if response.status == 404:
                    request_pages = False
                    continue
                if response.html:
                    page_results: List[str] = self.grep_html(
                        response.html, martyr_name
                    )
                    if page_results:
                        results.append(
                            SearchResult(
                                response.url, martyr_name, page_results
                            )
                        )
                        Logger.debug(
                            f"Found {len(page_results)} match(es) in {response.url}"
                        )
                    else:
                        Logger.debug(
                            f"Found no matches for {martyr_name} in {response.url}"
                        )
        return results


if __name__ == "__main__":
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.DEBUG,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    class TestSite(SinglePageQuerySite):
        Name = "AirWars"
        HomePage = "https://airwars.org"
        QueryTemplate: Final[str] = (
            "https://airwars.org/civilian-casualties/?"
            "belligerent=israeli-military"
            "&start_data=2023-10-07"
            "&country=the-gaza-strip"
            "&search={name}"
        )

    async def main():
        results = await TestSite().search_name("Lian")
        print(f"{results=}")

    asyncio.run(main())

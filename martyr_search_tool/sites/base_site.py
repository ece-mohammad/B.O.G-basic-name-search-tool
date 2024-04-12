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
from itertools import chain
from typing import Dict, Final, List, Tuple
from urllib import parse

import aiohttp
from anyio import open_file
from bs4 import BeautifulSoup

Logger: Final[log.Logger] = log.getLogger(__name__)
AgentsFile: Final[pathlib.Path] = pathlib.Path(__file__).parent / "agents.json"


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
        for line in parsed_html.text.split("\n"):
            if re.search(f"\\b{text}\\b", line, re.IGNORECASE):
                matches.append(line.strip())
        return matches

    @abc.abstractmethod
    async def search_setup(self):
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
    async def search_teardown(self):
        """Teardown any objects that were added to the class.

        It should close/terminate any objects started/initialized in setup. The
        method is called in search_names, after the search is completed.

        :return: None
        """
        ...

    @abc.abstractmethod
    async def search_name(self, martyr_name: str) -> List[SearchResult]:
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


class CurlGrepSite(BaseSite):
    """A Basic site where the response of a query URL is searched for names.

    BaseCurlGrepSite subclasses BaseSite and implements the search_name method
    to search for names in the response of a query URL. First, the query URL
    is constructed by replacing the {name} placeholder in the QueryTemplate
    with the name to search for. Then, the response of the query URL is
    searched for the name using Regex. The search is case-insensitive.
    The results contain the lines in the response that contain the name.
    The results may contain duplicates.

    Class Attributes:
        - QueryTemplate: The query template for the site used to search for
        names. The query template must contain the {name} placeholder.
    """

    QueryTemplate: str = ""

    @staticmethod
    async def fetch_page(
        session: aiohttp.ClientSession, page_url: str
    ) -> Tuple[str, int, str | None]:
        """Get the contents of a web page

        :param session: aiohttp session
        :type session: aiohttp.ClientSession
        :param page_url: url of the page
        :type page_url: str
        :return: The url of the page and the content of the page, or None
        if the request failed (response code is not 200)
        :rtype: Tuple[str, str | None]
        """
        Logger.debug(f"Fetching page: {page_url}")
        async with session.get(page_url) as response:
            if response.status != 200:
                html = None
                Logger.error(
                    f"Error: {response.status} while fetching page: {page_url}"
                )
            else:
                html = await response.text(encoding="utf-8")
        return page_url, response.status, html

    async def search_setup(self):
        async with await open_file(AgentsFile) as f:
            contents: str = await f.read()
        agents: Dict[str, str] = json.loads(contents)
        self.user_agent: str = random.choice(agents)["ua"]
        self.headers: Dict[str, str] = {"User-Agent": self.user_agent}
        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            headers=self.headers
        )
        Logger.debug(f"{self.Name}: Using headers: {self.user_agent}")

    async def search_teardown(self):
        await self.session.close()

    async def search_name(self, martyr_name: str) -> List[SearchResult]:
        Logger.debug(f"Searching site: {self.Name} for name {martyr_name}...")
        query = self.QueryTemplate.format(name=parse.quote_plus(martyr_name))
        Logger.debug(f"Query: {query}")

        page_url, status_code, html = await self.fetch_page(
            self.session, query
        )

        if status_code != 200:
            return [SearchResult(page_url, martyr_name, None)]

        matches: List[str] = self.grep_html(html, martyr_name)
        if matches:
            Logger.debug(f"Found {len(matches)} match(es) in {page_url}")
        else:
            Logger.debug(f"No matches for {martyr_name} in {page_url}")
        return [SearchResult(page_url, martyr_name, matches)]


class PaginatedSite(CurlGrepSite):
    """A Subclass of CurlGrepSite for sites that have pagination.

    Pages are cycled through until the response is not found (RC 404). The
    QueryTemplate must contain the {page} placeholder, in addition to the
    {name} placeholder.

    Methods:
        - next_page: Returns the url of the next page
    """

    QueryTemplate: str = ""

    async def search_name(self, martyr_name: str) -> List[SearchResult]:
        page = 1
        Logger.debug(f"Searching for name {martyr_name} in {self.Name}...")
        query = self.QueryTemplate.format(
            name=parse.quote_plus(martyr_name),
            page="{page}",
        )
        results: List[SearchResult] = []

        request_pages: bool = True
        while request_pages:
            tasks = [
                self.fetch_page(self.session, query.format(page=page))
                for page in range(page, page + 5)
            ]
            page += 5
            responses = await asyncio.gather(*tasks)
            for page_url, status_code, html in responses:
                if status_code == 404:
                    request_pages = False
                elif html is not None:
                    page_results: List[str] = self.grep_html(html, martyr_name)
                    if page_results:
                        results.append(
                            SearchResult(page_url, martyr_name, page_results)
                        )
                        Logger.debug(
                            f"Found {len(page_results)} match(es) in {page_url}"
                        )
                    else:
                        Logger.debug(
                            f"Found no matches for {martyr_name} in {page_url}"
                        )
        return results


if __name__ == "__main__":
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.DEBUG,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    class TestSite(CurlGrepSite):
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

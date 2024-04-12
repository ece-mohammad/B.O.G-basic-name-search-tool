#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# ourgaza.com

The site is a bit similar to aintnumbers, in that it contains article about
martyrs in Gaza under the ourgaza.com/martyrs page, but it doesn't have a
search functionality. However, it has a filter for teens, children, adults,
and seniors to filter out displayed articles.

The site has pagination, each page has 20 articles.
Each article is named after the martyr, so searching for a name in a list of
articles is straight forward.

- Pattern for all articles:
    https://ourgaza.com/martyrs/{page_number}
- Pattern for articles filtered for teen martyrs:
    https://ourgaza.com/martyrs/filter/teen/{page}
- Pattern for articles filtered for children martyrs:
    https://ourgaza.com/martyrs/filter/children/{page}

## Strategy

1. Get the first page that contains all articles:
    https://ourgaza.com/martyrs/1,
    page_number=1
2. search for an article that contains the name.
3. Increment page_number, and repeat from step 1 till we get a 404 Error.

"""
import asyncio
from itertools import chain
from typing import List

from martyr_search_tool.sites import base_site
from martyr_search_tool.sites.base_site import SearchResult


class _OurGhazaFirstPage(base_site.CurlGrepSite):
    Name: str = "OurGaza"
    HomePage: str = "https://ourgaza.com/"
    QueryTemplate: str = "https://ourgaza.com/martyrs"


class _OurGhazaPages(base_site.PaginatedSite):
    Name: str = "OurGaza"
    HomePage: str = "https://ourgaza.com/"
    QueryTemplate: str = "https://ourgaza.com/martyrs/{page}"


class OurGhaza(base_site.BaseSite):
    Name: str = "OurGaza"
    HomePage: str = "https://ourgaza.com/"
    QueryTemplate: str = "https://ourgaza.com/martyrs/{page}"

    def __init__(self, *args, **kwargs):
        self.sites = [_OurGhazaFirstPage(), _OurGhazaPages()]

    async def search_setup(self):
        await asyncio.gather(*[site.search_setup() for site in self.sites])
        self.sites[1].page = 2

    async def search_teardown(self):
        await asyncio.gather(*[site.search_teardown() for site in self.sites])

    async def search_name(self, martyr_name: str) -> List[SearchResult]:
        search_results: List[List[SearchResult]] = await asyncio.gather(
            *[site.search_name(martyr_name) for site in self.sites]
        )

        return list(chain(*search_results))


if __name__ == "__main__":
    ...

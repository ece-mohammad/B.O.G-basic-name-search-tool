#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Searches aintnumbers.com for martyrs by name

## Brief

The site contains articles for martyred children, each article is named after
a martyred child. The site allows searching article by text.
A search query can be constructed using the following pattern: A search query
can be constructed https://www.aintnumbers.com/?s={search_query}
Search results are paginated, It's possible to iterate the results pages using
the pattern https://www.aintnumbers.com/page/{pagination}/?s={search_query}.

## Strategy

    1. Construct a search query by substituting the name for the search_query
    in the search query pattern.
    2. Grab the results page.
    3. Check the page source for the name.
    4. Iterate the search pages til a 404 Error is returned.

"""


import asyncio

from martyr_search_tool.sites.base_site import PaginatedSite


class AintNumbers(PaginatedSite):
    """Searches aintnumbers.com for martyrs by name"""

    Name: str = "AintNumbers"
    HomePage: str = "https://www.aintnumbers.com/"
    QueryTemplate: str = "https://www.aintnumbers.com/page/{page}/?s={name}"


if __name__ == "__main__":
    import logging as log
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.DEBUG,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    async def main():
        results = await AintNumbers().search_name("Lian")
        print(f"{results=}")

    asyncio.run(main())

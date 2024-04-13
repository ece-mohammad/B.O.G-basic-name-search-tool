#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# letthemgrowup.com

The site contains a table with the names of martyred children and teens,
their names, and links to the sources.

## Strategy

1. Get the website's page https://letthemgrowup.com/children-we-already-lost-en/.
2. Search the page source for the name.

"""

from typing import List

from martyr_search_tool.sites import base_site


class LetThemGrowUp(base_site.SinglePageSite):
    Name: str = "LetThemGrowUp"
    HomePage: str = "https://letthemgrowup.com"
    URLS: List[str] = [
        "https://letthemgrowup.com/children-we-already-lost-en/",
    ]


if __name__ == "__main__":
    ...

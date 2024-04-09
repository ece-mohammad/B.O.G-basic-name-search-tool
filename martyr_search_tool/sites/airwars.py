#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Searches airwars.org for martyrs by name

## Brief

The website has an incidents archive that can be searched and filtered by:
    - Belligerent
    - Country
    - start date
    - end date
    - Civilian Harm Status
    - Belligerent Assessment
    - Declassified Documents
    - Infrastructure
    - text search

The search functionality uses the previous filters and displays all incidents
that match them. A search query can be constructed by setting the following
search filters in the URL:

    **filter**  |   **URL filter** | **Value**
    -----------:|:----------------:|:-------------
    Belligerent | belligerent      | israeli-military
    Country     | country          | the-gaza-strip
    Start date  | start_date       | 2023-10-07
    Search      | search           | {name}`

    name must be URL encoded and spaces can be replaced by dashes -

Names can be looked up using the following pattern:
https://airwars.org/civilian-casualties/?belligerent=israeli-military&start_data=2023-10-07&country=the-gaza-strip&search={name}

## Strategy

    1. construct the search query using the search query template
    2. grab the result page
    3. search the page source for the name

"""


import asyncio

from martyr_search_tool.sites.base_site import CurlGrepSite


class AirWars(CurlGrepSite):
    """Searches airwars.org for martyrs by name"""

    Name: str = "AirWars"
    HomePage: str = "https://airwars.org"
    QueryTemplate: str = (
        "https://airwars.org/civilian-casualties/?"
        "belligerent=israeli-military"
        "&start_data=2023-10-07"
        "&country=the-gaza-strip"
        "&search={name}"
    )


if __name__ == "__main__":
    import logging as log
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.DEBUG,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    async def main():
        results = await AirWars().search_name("Lian")
        print(f"{results=}")

    asyncio.run(main())

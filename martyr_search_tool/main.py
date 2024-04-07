#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import asyncio
import logging as log
from typing import Final, List

import tabulate

from martyr_search_tool.sites import airwars
from martyr_search_tool.sites.base_site import SearchResult

Logger: Final[log.Logger] = log.getLogger(__name__)

SearchSites: List = [
    airwars.AirWars(),
]


def print_results(results: List[SearchResult]) -> None:
    table_headers: List[str] = ["name", "count", "url"]
    table_data: List[List[str]] = []
    for result in results:
        if result.instances is None:
            continue
        table_data.append([result.name, len(result.instances), result.url])
    table: str = tabulate.tabulate(
        table_data, headers=table_headers, tablefmt="pretty"
    )
    print(table)


async def main(args: List[str]) -> None:
    arg_parser = argparse.ArgumentParser(
        description="A command line tool that searches multiple sites related "
        "to the attacks of the Israeli apartheid on Palestinian "
        "civilians for martyr names",
    )

    arg_parser.add_argument(
        "names",
        help="""The name of the martyr to search for, the name is case
        insensitive. If the name contains multiple words, it should be enclosed
        in double quotes. For example, "Lian Hussein".""",
        type=str,
        nargs="+",
        action="store",
    )

    args = arg_parser.parse_args(args)
    search_results: List[SearchResult] = list()
    for martyr_name in args.names:
        Logger.debug(f"searching for name: {martyr_name}")
        for site in SearchSites:
            site_results: SearchResult = await site.search_name(martyr_name)
            search_results.append(site_results)
    print_results(search_results)


if __name__ == "__main__":
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.ERROR,
        format="%(name)s:%(levelname)s:%(message)s",
    )

    asyncio.run(main(sys.argv[1:]))

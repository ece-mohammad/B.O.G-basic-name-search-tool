#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import asyncio
import logging as log
from itertools import chain
from typing import Final, List

import tabulate

from martyr_search_tool.sites import airwars, aitnumbers, let_them_grow_up
from martyr_search_tool.sites.base_site import SearchResult

Logger: Final[log.Logger] = log.getLogger(__name__)

SearchSites: List = [
    airwars.AirWars(),
    aitnumbers.AintNumbers(),
    let_them_grow_up.LetThemGrowUp(),
]


def print_results(results: List[SearchResult]) -> None:
    """Prints search results to the console in a table format.

    :param results: A list of search results
    :type results: List[SearchResult]
    :return: None
    """
    table_headers: List[str] = ["name", "count", "url"]
    table_data: List[List[str]] = []
    total_matches: int = 0
    for result in results:
        if result.instances is None:
            continue
        table_data.append([result.name, len(result.instances), result.url])
        total_matches += len(result.instances)
    table: str = tabulate.tabulate(
        table_data, headers=table_headers, tablefmt="pretty"
    )
    print(table)
    print(f"total matches: {total_matches}")


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
    tasks = [site.search_names(args.names) for site in SearchSites]
    search_results = await asyncio.gather(*tasks)
    print_results(list(chain(*search_results)))


if __name__ == "__main__":
    import sys

    log.basicConfig(
        stream=sys.stdout,
        level=log.INFO,
        format="%(levelname)s:%(name)s:%(lineno)d:%(message)s",
    )

    asyncio.run(main(sys.argv[1:]))

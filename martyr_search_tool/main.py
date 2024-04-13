#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import asyncio
import logging as log
from itertools import chain
from typing import Any, Dict, Final, List

import tabulate

from martyr_search_tool.sites import (
    airwars,
    aitnumbers,
    let_them_grow_up,
    our_ghaza,
    twitter
)
from martyr_search_tool.sites.base_site import SearchResult

Logger: Final[log.Logger] = log.getLogger(__name__)

SearchSites: List = [
    airwars.AirWars(),
    aitnumbers.AintNumbers(),
    let_them_grow_up.LetThemGrowUp(),
    our_ghaza.OurGhaza(),
    twitter.Twitter()
]


async def print_results(results: List[SearchResult]) -> None:
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


async def configure_logging(enable_debug: bool = False) -> None:
    """Configure logging for the application. By default, the logging level is
    INFO. If enable_debug is True, the logging level is set to DEBUG.

    :param enable_debug: Enable debug logging
    :type enable_debug: bool
    :return: None
    """
    if enable_debug:
        log_level = log.DEBUG
    else:
        log_level = log.INFO

    log.basicConfig(
        stream=sys.stdout,
        level=log_level,
        format="%(levelname)s:%(name)s:%(lineno)d:%(message)s",
    )


async def search_names(names: List[str]) -> List[SearchResult]:
    """Search list of sites in SearchSite for the given names.

    :param names: A list of names
    :type names: List[str]
    :return: A list of SearchResult that contains the results of the search
    for each site.
    :rtype: List[SearchResult]
    """
    tasks = [site.search_names(names) for site in SearchSites]
    search_results: List[List[SearchResult]] = await asyncio.gather(*tasks)
    return list(chain(*search_results))


def configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A command line tool that searches multiple sites related "
        "to the attacks of the Israeli apartheid on Palestinian "
        "civilians for martyr names",
    )

    parser.add_argument(
        "names",
        help="""The name of the martyr to search for, the name is case
            insensitive. If the name contains multiple words, it should be 
            enclosed in double quotes. For example, "Lian Hussein".""",
        type=str,
        nargs="+",
        action="store",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print debugging information",
    )

    return parser


def parse_args(args: List[str]) -> Dict[str, Any]:
    """Parse arguments from a list and return the positional and optional
    arguments as a dictionary.

    Example:
    >>> parse_args(['--verbose', 'Lian Hussein'])
    {'verbose': True, 'names': ['Lian Hussein']}

    :param args: A list of arguments
    :type args: List[str]
    :return: A dictionary of arguments
    :rtype: Dict[str, Any]
    """
    arg_parser: argparse.ArgumentParser = configure_parser()
    args = arg_parser.parse_args(args)
    return vars(args)


async def main(args: List[str]) -> None:
    args = parse_args(args)
    await configure_logging(args["verbose"])
    search_results: List[SearchResult] = await search_names(args["names"])
    await print_results(search_results)


if __name__ == "__main__":
    import sys

    asyncio.run(main(sys.argv[1:]))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple CLI to search for tweets on twitter that contains a given string, 
or any of its permutations
"""

import asyncio
import sys
import tomllib
from itertools import permutations
from pathlib import Path
from typing import *

from twikit import Tweet
from twikit.errors import TwitterException
from twikit.twikit_async import Client

# Path to configuration file that contains Twitter login credentials
CONFIG_FILE: Final[Path] = Path("./twitter.toml")

# Path to cookies file, used to skip logging in each time the tool is used
COOKIES_FILE: Final[Path] = Path("./.twitter_cookies")


def get_credentials(file: Path) -> Dict[str, str] | None:
    """Get credentials to user for Twitter login from configuration file

    :param file: path to a toml file that contains twitter credentials
    :type file: pathlib.Path
    :return: credentials from the file, or None if `file` is not a file
    or doesn't exist
    :rtype: Dict[str, str]
    :return: None
    """
    if not file.is_file():
        return None
    return tomllib.loads(file.read_text())


async def client_login(
    client: Client,
    email: str,
    username: str,
    password: str,
    cookies_file: Path = COOKIES_FILE,
) -> Dict[str, Any] | None:
    """Attempt to log in a twitter client using given credentials

    :param client: a twitter client, must be initialized before logging in
    :type client: twikit.twikit_async.Client
    :param email: twitter account's email
    :type email: str
    :param username: twitter account's username
    :type username: str
    :param password: twitter account's password
    :type password: str
    :param cookies_file: path to twitter client's cookies file, to use instead of logging in
    :type cookies_file: pathlib.Path
    :return: client's login response
    :rtype: Dict[str, Any]
    """

    # if cookies file exists, load cookies
    if cookies_file and cookies_file.is_file():
        client.load_cookies(cookies_file)
        return {"status": "success"}

    try:
        # attempt to login
        await client.login(auth_info_1=email, auth_info_2=username, password=password)

    except TwitterException as tw_exc:
        # BadRequest -> bad credentials
        return {"status": tw_exc}

    else:
        # if login was a success, save cookies for future runs
        client.save_cookies(cookies_file)

    return {"status": "success"}


def get_unique_name_variations(name: List[str]) -> List[str]:
    """list all possible unique variations of a name

    Example:
    ========
        get_unique_name_variations(["foo", "bar", "foo"])
        >>> "foo bar foo", "foo foo bar", "bar foo foo"

    :param name: a name as a list of strings
    :type name: List[str]
    :return: a list of space spearated strings, each string represents a unique variation of the input name
    :rtype: List[str]
    """
    variations = [" ".join(p) for p in permutations(name)]
    return list(set(variations))


def create_tweet_link(tweet: Tweet) -> str:
    """Create a link to the given tweet

    :param tweet: a tweet object
    :type tweet: twikit.Tweet
    :return: a URL to the tweet
    :rtype: str
    """
    return f"https://twitter.com/{tweet.user.name}/status/{tweet.id}"


async def get_tweets_containing_term(client: Client, search_term: str) -> List[Tweet]:
    """Gets all tweets containing the given search term

    :param client: a twitter client that is logged in using `client_login`
    :type client: twikit.twikit_async.Client
    :param search_term: a string that is used to search for tweets
    :type search_term: str
    :return: a list of tweets that contain the search term
    :rtype: List[Tweet]
    :raises: twikit.errors.TooManyRequests when too many requests are made and twitter
    API rate limit is exceeded
    """
    results = list()

    try:
        # get tweets that contain search_term
        tweets = await client.search_tweet(search_term, "Top")

    except TwitterException as tw_exc:
        print(f"Searching tweets for {search_term} failed due to error: {tw_exc}")
        return []

    else:
        # append tweets to results
        for tweet in tweets:
            results.append(tweet)

    return results


async def get_tweets_containing_name(client: Client, name: List[str]) -> List[str]:
    """Get all tweets that contain the name or one of its variations"""
    found_tweets = list()

    # get all permutations of name
    name_variateions = get_unique_name_variations(name)
    async with asyncio.TaskGroup() as tg:
        # create a task for each name to search for tweets that contain that name
        tasks = [
            tg.create_task(get_tweets_containing_term(client, variant))
            for variant in name_variateions
        ]

    # check results of each task
    for task in tasks:
        try:
            tweets = task.result()

        except Exception as exc:
            pass

        else:
            for tweet in tweets:
                if tweet not in found_tweets:
                    found_tweets.append(tweet)

    return found_tweets


async def main():
    # get credentials from config file
    credentials = get_credentials(CONFIG_FILE)

    # create a client instance
    twitter_cli = Client(language="en-US")

    # login to twitter
    response = await client_login(
        twitter_cli,
        credentials["username"],
        credentials["email"],
        credentials["password"],
        COOKIES_FILE,
    )

    # check login status
    if response["status"] != "success":
        print(f"Failed to login to twitter, error message: {response['status']}")
        sys.exit(-1)

    # get name from command line
    search_name = sys.argv[1:]
    if not search_name:
        print("Error! you must provide a name.")
        sys.exit(-1)

    # search twitter for name
    tweets = await get_tweets_containing_name(twitter_cli, search_name)

    # print links to found tweets
    for tweet in tweets:
        print(create_tweet_link(tweet))


if __name__ == "__main__":
    asyncio.run(main())

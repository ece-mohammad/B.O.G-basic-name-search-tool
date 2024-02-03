#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple CLI to search for tweets on twitter that contains a given string, 
or any of its permutations
"""

import sys
import tomllib
from itertools import permutations
from pathlib import Path
from typing import *

from twikit import Client, Tweet

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


def client_login(
    client: Client,
    email: str,
    username: str,
    password: str,
    cookies_file: Path = COOKIES_FILE,
) -> Dict[str, Any] | None:
    """Attempt to log in a twitter client using given credentials

    :param client: an instance of Twikit's Twitter client
    :type client: twikit.client.Client
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
    if cookies_file and cookies_file.is_file():
        client.load_cookies(cookies_file)
        response = {"status": "success"}

    else:
        response = client.login(
            auth_info_1=email, auth_info_2=username, password=password
        )

        if response["status"] == "success":
            client.save_cookies(cookies_file)

    return response


def get_unique_name_variations(name: List[str]) -> List[str]:
    """list all possible unique variations of a name

    Example:
        get_unique_name_variations(["foo", "bar", "foo"])
        >>> "foo bar foo", "foo foo bar", "bar foo foo"

    :param name: a name as a list of strings
    :type name: List[str]
    :return: a list of space spearated strings, each string represents a unique variation of the input name
    :rtype: List[str]
    """
    return list(set(" ".join(list(p)) for p in permutations(name)))


def create_tweet_link(tweet: Tweet) -> str:
    """Create a link to the given tweet"""
    return f"https://twitter.com/{tweet.user.name}/status/{tweet.id}"


def get_tweets_containing_term(client: Client, search_term: str) -> List[Tweet]:
    """Gets all tweets containing the given search term"""
    results = list()
    tweets = client.search_tweet(search_term, "Top")
    for tweet in tweets:
        results.append(tweet)
    return results


def get_tweets_containing_name(client: Client, name: List[str]) -> List[str]:
    """Get all tweets that contain the name or one of its variations"""
    found_tweets = list()

    name_variateions = get_unique_name_variations(name)
    for variant in name_variateions:
        tweets = get_tweets_containing_term(client, variant)
        for tweet in tweets:
            if tweet not in found_tweets:
                found_tweets.append(tweet)

    return found_tweets


def main():
    credentials = get_credentials(CONFIG_FILE)
    twitter_cli = Client(language="en-US")
    response = client_login(
        twitter_cli,
        credentials["username"],
        credentials["email"],
        credentials["password"],
        COOKIES_FILE,
    )

    if response["status"] != "success":
        print(
            f"Failed to login to X using credentials: {credentials['username']}, {credentials['email']}"
        )
        sys.exit(-1)

    # get name from command line
    search_name = sys.argv[1:]

    # search twitter for name
    tweets = get_tweets_containing_name(twitter_cli, search_name)

    # print links to found tweets
    for tweet in tweets:
        print(create_tweet_link(tweet))


if __name__ == "__main__":
    main()

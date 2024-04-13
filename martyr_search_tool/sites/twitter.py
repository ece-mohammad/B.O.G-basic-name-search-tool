#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple CLI to search for tweets on twitter that contains a given string.

The client uses Twikit, a Twitter API wrapper that doesn't require an API key.
But it requires a user account. Twitter account configurations are stored in a
configuration file called `config.toml`. That file should be in the sa
directory as the tool, it should contain the username, email and password.

"""

import logging as log
from pathlib import Path
import re
import tomllib
from typing import Dict, Final, List, Any

from twikit import Tweet
from twikit.errors import TwitterException
from twikit.twikit_async import Client

from martyr_search_tool.sites import base_site
from martyr_search_tool.sites.base_site import SearchResult

Logger: Final[log.Logger] = log.getLogger(__name__)

# Path to configuration file that contains Twitter login credentials
CONFIG_FILE: Final[Path] = Path(__file__).parent.parent / "config.toml"

# Path to cookies file, used to skip logging in each time the tool is used
COOKIES_FILE: Final[Path] = Path(__file__).parent.parent / ".twitter_cookies"


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
    return tomllib.loads(file.read_text())["twitter"]


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
        await client.login(
            auth_info_1=email, auth_info_2=username, password=password
            )

    except TwitterException as tw_exc:
        # BadRequest -> bad credentials
        return {"status": tw_exc}

    else:
        # if login was a success, save cookies for future runs
        client.save_cookies(cookies_file)

    return {"status": "success"}


def create_tweet_link(tweet: Tweet) -> str:
    """Create a link to the given tweet

    :param tweet: a tweet object
    :type tweet: twikit.Tweet
    :return: a URL to the tweet
    :rtype: str
    """
    return f"https://twitter.com/{tweet.user.name}/status/{tweet.id}"


async def get_tweets_containing_term(client: Client, search_term: str) -> List[
    Tweet]:
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
        print(
            f"Searching tweets for {search_term} failed due to error: {tw_exc}"
            )
        return []

    else:
        # append tweets to results
        for tweet in tweets:
            results.append(tweet)

    return results


class Twitter(base_site.BaseSite):
    Name: str = "Twitter"
    HomePage: str = "https://twitter.com"

    def __init__(self):
        # get credentials from config file
        self.credentials: Dict[str, str] = get_credentials(CONFIG_FILE)

        # create a client instance
        self.client: Client = Client(language="en-US")

    async def search_setup(self) -> None:
        response = await client_login(
            self.client,
            self.credentials["username"],
            self.credentials["email"],
            self.credentials["password"],
            COOKIES_FILE,
        )

        if response["status"] != "success":
            Logger.error(
                f"Failed to login to twitter, error message: {response['status']}"
            )

    async def search_teardown(self) -> None:
        pass

    async def search_name(self, martyr_name: str, **kwargs) -> List[SearchResult]:
        tweets: List[Tweet] = await get_tweets_containing_term(
            self.client,
            martyr_name
        )
        search_results: List[SearchResult] = [
            SearchResult(
                create_tweet_link(tweet),
                martyr_name,
                [
                    line.strip() for line in tweet.text.split() if
                    re.search(f"\\b{martyr_name}\\b", line)
                ]
            )
            for tweet in tweets
        ]

        return search_results


if __name__ == "__main__":
    ...

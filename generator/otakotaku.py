# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

# This file is part of 'ids.moe'. It is a derivative work of
# code from the 'animeApi' project by 'nattadasu'. The original license notices
# are preserved in the `NOTICE` file in the root of this repository.

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional, Union

import requests
from requests.adapters import HTTPAdapter, Retry
from alive_progress import alive_bar
from bs4 import BeautifulSoup, Tag
from generator.const import pprint
from generator.prettyprint import Platform, Status


class OtakOtaku:
    """OtakOtaku anime data scraper (Optimized and Safer)"""

    def __init__(self) -> None:
        """Initiate the class with a persistent and resilient session."""
        self.session = requests.Session()

        # Strategy: Implement automatic retries with exponential backoff.
        # This tells requests to retry on common server errors (5xx) or rate-limit codes (429).
        # It will wait {backoff factor} * (2 ** ({number of retries} - 1)) seconds.
        # e.g., for backoff_factor=0.5: 0.5s, 1s, 2s, 4s, 8s
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        # Strategy: Simplify headers and use a standard User-Agent.
        self.session.headers.update(
            {
                "Referer": "https://otakotaku.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        pprint.print(
            Platform.OTAKOTAKU,
            Status.READY,
            "OtakOtaku anime data scraper ready to use",
        )

    def _get(self, url: str) -> Optional[requests.Response]:
        """
        Get the response from the url using the resilient session.
        Retries are handled automatically by the session.

        :param url: The url to get the response
        :return: The response from the url or None on final error
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response
        except requests.RequestException as err:
            pprint.print(
                Platform.OTAKOTAKU,
                Status.ERR,
                f"Request failed for {url} after retries: {err}",
            )
            return None

    def get_latest_anime(self) -> int:
        """
        Get latest anime from the website.
        """
        url = "https://otakotaku.com/anime/feed"
        response = self._get(url)
        if not response:
            raise ConnectionError(
                "Failed to connect to otakotaku.com to get latest ID."
            )

        soup = BeautifulSoup(response.text, "html.parser")
        link_tag = soup.select_one("div.anime-img > a")  # Robust CSS selector

        if not isinstance(link_tag, Tag) or not link_tag.get("href"):
            pprint.print(
                Platform.OTAKOTAKU, Status.ERR, "Failed to parse latest anime ID."
            )
            return 0

        href = link_tag["href"]
        if isinstance(href, list):
            href = href[0]

        anime_id_str = href.rstrip("/").split("/")[-2]
        if not anime_id_str.isdigit():
            pprint.print(
                Platform.OTAKOTAKU,
                Status.ERR,
                f"Could not extract a valid anime ID from href: {href}",
            )
            return 0

        anime_id = int(anime_id_str)
        pprint.print(Platform.OTAKOTAKU, Status.PASS, f"Latest anime id: {anime_id}")
        return anime_id

    def _get_data(self, anime_id: int) -> Optional[dict[str, Any]]:
        """
        Get anime data for a single ID with a polite delay.
        This function is the target for our concurrent calls.
        """
        # Strategy: Add a small, random delay to each worker task to appear more "human".
        time.sleep(random.uniform(0.1, 0.4))

        # The trailing part of the URL is ignored by the API, so we can simplify it.
        url = f"https://otakotaku.com/api/anime/view/{anime_id}"
        response = self._get(url)
        if not response:
            return None

        try:
            json_ = response.json()
        except requests.JSONDecodeError:
            # This is expected for non-existent IDs which return HTML error pages.
            return None

        if not json_ or "data" not in json_ or not json_["data"]:
            # This is a common case for IDs that don't exist. We can ignore it.
            return None

        data: dict[str, Any] = json_["data"]

        def to_int(value: Any) -> Optional[int]:
            return int(value) if value else None

        title = data.get("judul_anime", "").replace('"""', '"')
        if not title:
            return None  # Skip entries without a title

        result: dict[str, Union[str, int, None]] = {
            "otakotaku": to_int(data.get("id_anime")),
            "title": title,
            "myanimelist": to_int(data.get("mal_id_anime")),
            "animeplanet": to_int(data.get("ap_id_anime")),
            "anidb": to_int(data.get("anidb_id_anime")),
            "animenewsnetwork": to_int(data.get("ann_id_anime")),
        }
        return result

    def get_anime(self) -> list[dict[str, Any]]:
        """
        Get complete anime data concurrently and safely.
        """
        pprint.print(
            Platform.OTAKOTAKU,
            Status.INFO,
            "Starting safer concurrent anime data collection",
        )

        latest_id = self.get_latest_anime()
        if not latest_id:
            raise ValueError("Could not determine the latest anime ID to scrape.")

        anime_list: list[dict[str, Any]] = []

        # Strategy: Use a conservative number of workers to avoid IP bans.
        # Start here. You can try increasing to 20 or 25 if no errors occur.
        MAX_WORKERS = 25

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all jobs to the executor
            futures = {
                executor.submit(self._get_data, anime_id): anime_id
                for anime_id in range(1, latest_id + 1)
            }

            # Use alive_bar to track progress as futures complete
            with alive_bar(
                latest_id, title="Getting OtakOtaku data", spinner=None
            ) as bar:
                for future in as_completed(futures):
                    data_index = future.result()
                    if data_index:
                        anime_list.append(data_index)
                    bar()  # Manually advance the progress bar for each completed task

        # Sorting is done once at the end, which is efficient.
        anime_list.sort(key=lambda x: x["title"])

        pprint.print(
            Platform.OTAKOTAKU,
            Status.PASS,
            f"Total anime data collected: {len(anime_list)}",
        )
        return anime_list

    @staticmethod
    def convert_list_to_dict(data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Convert list to dict.
        """
        result: dict[str, dict[str, Any]] = {}
        for item in data:
            # Add a check to ensure the key exists and is not None
            if "otakotaku" in item and item["otakotaku"] is not None:
                result[str(item["otakotaku"])] = item
        return result

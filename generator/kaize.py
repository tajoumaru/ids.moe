# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

# This file is part of 'ids.moe'. It is a derivative work of
# code from the 'animeApi' project by 'nattadasu'. The original license notices
# are preserved in the `NOTICE` file in the root of this repository.

import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

import requests
from requests.adapters import HTTPAdapter, Retry
from alive_progress import alive_bar
from bs4 import BeautifulSoup
from generator.const import pprint
from generator.prettyprint import Platform, Status


class Kaize:
    """Kaize anime data scraper (Optimized and Session-Based)"""

    def __init__(self, email: str, password: str) -> None:
        if not email or not password:
            raise ValueError("Email and password cannot be empty.")

        self.base_url = "https://kaize.io"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            }
        )

        retries = Retry(
            total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        # Perform login
        self._login(email, password)

        pprint.print(
            Platform.KAIZE, Status.READY, "Kaize anime data scraper ready to use."
        )

    def _login(self, email: str, password: str) -> None:
        """
        Perform login to Kaize.io using email and password.
        """
        pprint.print(Platform.KAIZE, Status.INFO, "Logging in to Kaize...")
        
        # Step 1: Get the login page to retrieve CSRF token and initial cookies
        login_page_url = f"{self.base_url}/login"
        try:
            response = self.session.get(login_page_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to access login page: {e}")
        
        # Parse CSRF token from HTML
        soup = BeautifulSoup(response.text, "html.parser")
        csrf_meta = soup.find("meta", {"name": "csrf-token"})
        if not csrf_meta or not csrf_meta.get("content"):
            raise ValueError("Failed to retrieve CSRF token from login page")
        
        csrf_token = csrf_meta["content"]
        
        # Step 2: Perform login POST request
        login_url = f"{self.base_url}/login"
        login_data = {
            "_token": csrf_token,
            "email": email,
            "password": password,
            "remember": "on"
        }
        
        try:
            response = self.session.post(
                login_url, 
                data=login_data,
                timeout=15,
                allow_redirects=False
            )
            
            # Check if login was successful (302 redirect is expected)
            if response.status_code == 302:
                pprint.print(Platform.KAIZE, Status.PASS, "Successfully logged in to Kaize")
                
                # Extract XSRF token from cookies for future requests
                xsrf_token = self.session.cookies.get("XSRF-TOKEN")
                if xsrf_token:
                    self.session.headers.update({
                        "X-XSRF-TOKEN": xsrf_token,
                    })
            else:
                raise ConnectionError(f"Login failed with status code: {response.status_code}")
                
        except requests.RequestException as e:
            raise ConnectionError(f"Login request failed: {e}")

    def _verify_session(self) -> bool:
        pprint.print(Platform.KAIZE, Status.INFO, "Verifying session...")
        verify_url = f"{self.base_url}/account/settings"
        try:
            response = self.session.get(verify_url, timeout=15, allow_redirects=False)
            if response.status_code == 200:
                pprint.print(Platform.KAIZE, Status.PASS, "Session is valid.")
                return True
            pprint.print(
                Platform.KAIZE,
                Status.ERR,
                f"Session is invalid or expired (Status: {response.status_code}). Please provide new cookies.",
            )
            return False
        except requests.RequestException as e:
            pprint.print(Platform.KAIZE, Status.ERR, f"Failed to verify session: {e}")
            return False

    def _page_exists(
        self, page: int, media: Literal["anime", "manga"] = "anime"
    ) -> bool:
        """
        Helper function to check if a given page number contains content.
        """
        url = f"{self.base_url}/{media}/top?page={page}"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return False
            soup = BeautifulSoup(response.text, "html.parser")
            # A page is considered to "exist" if it has at least one anime element.
            return soup.find("div", {"class": "anime-list-element"}) is not None
        except requests.RequestException:
            return False

    def _find_last_page(self, media: Literal["anime", "manga"] = "anime") -> int:
        """
        Finds the last page number using an efficient binary search probing method.
        This is the correct optimization for a site with only a "Next" button.
        """
        pprint.print(
            Platform.KAIZE, Status.INFO, "Finding last page using binary search..."
        )

        # Step 1: Find an upper bound exponentially.
        low = 1
        high = 1
        while self._page_exists(high, media):
            low = high
            high *= 2
            pprint.print(
                Platform.KAIZE,
                Status.INFO,
                f"Last page is at least {low}, checking {high}...",
                clean_line=True,
                end="",
            )

        pprint.print(
            Platform.KAIZE,
            Status.INFO,
            f"Found upper bound. Last page is between {low} and {high}.",
        )

        # Step 2: Perform binary search between low and high.
        last_known_good = low
        while low <= high:
            mid = (low + high) // 2
            if mid == 0:
                break  # Safety break
            pprint.print(
                Platform.KAIZE,
                Status.INFO,
                f"Searching... Low: {low}, Mid: {mid}, High: {high}",
                clean_line=True,
                end="",
            )
            if self._page_exists(mid, media):
                last_known_good = mid
                low = mid + 1
            else:
                high = mid - 1

        pprint.print(
            Platform.KAIZE,
            Status.PASS,
            f"Binary search complete. Last page is {last_known_good}.",
        )
        return last_known_good

    def _scrape_page(
        self, page: int, media: Literal["anime", "manga"] = "anime"
    ) -> list[dict[str, Any]]:
        # This method is correct and remains unchanged
        time.sleep(random.uniform(0.3, 1.0))
        url = f"{self.base_url}/{media}/top?page={page}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        kz_dat = soup.find_all("div", {"class": "anime-list-element"})
        result: list[dict[str, Any]] = []
        for kz in kz_dat:
            title_tag = kz.find("a", {"class": "name"})
            cover_div = kz.find("div", {"class": "cover"})
            if not (
                title_tag
                and title_tag.get("href")
                and cover_div
                and cover_div.get("style")
            ):
                continue
            title: str = title_tag.text
            slug: str = title_tag["href"].split("/")[-1]
            media_id_match = re.search(r"/anime_image_(\d+)", cover_div["style"])
            media_id = int(media_id_match.group(1)) if media_id_match else 0
            result.append({"title": title, "slug": slug, "kaize": media_id})
        return result

    def get_anime(self) -> list[dict[str, Any]]:
        if not self._verify_session():
            raise ConnectionError("Unable to proceed with an invalid session.")

        pprint.print(Platform.KAIZE, Status.INFO, "Starting anime data collection")
        total_pages = self._find_last_page()
        if total_pages == 0:
            return []

        anime_data: list[dict[str, Any]] = []
        MAX_WORKERS = 8

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._scrape_page, page): page
                for page in range(1, total_pages + 1)
            }

            with alive_bar(
                total_pages, title="Getting Kaize data", spinner=None
            ) as bar:
                for future in as_completed(futures):
                    page_data = future.result()
                    if page_data:
                        anime_data.extend(page_data)
                    bar()

        anime_data.sort(key=lambda x: x["title"])

        pprint.print(
            Platform.KAIZE,
            Status.PASS,
            f"Done getting data. Total items: {len(anime_data)} from {total_pages} pages.",
        )
        return anime_data

    @staticmethod
    def convert_list_to_dict(data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in data:
            if "slug" in item:
                result[item["slug"]] = item
        return result

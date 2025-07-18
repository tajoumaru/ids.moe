# SPDX-License-Identifier: MIT

import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

import cloudscraper  # type: ignore
from alive_progress import alive_bar
from bs4 import BeautifulSoup, Tag
from generator.const import pprint
from generator.prettyprint import Platform, Status
from requests.adapters import Retry
from requests import Response


def nautiljon_extract_table(html_content: str) -> list[dict[str, str | int | None]]:
    """
    Extract the table data from the html content, only for Nautiljon.
    This version is more robust against missing elements.

    :param html_content: The html content
    :return: The table data
    """
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", class_="search")
    if not isinstance(table, Tag):
        return []

    tbody = table.find("tbody")
    if not isinstance(tbody, Tag):
        return []

    data_list: list[dict[str, str | int | None]] = []
    rows = tbody.find_all("tr")

    for row in rows:
        columns = row.find_all("td")
        if len(columns) < 4:
            continue

        # Safely extract data with checks
        title_tag = columns[1].find("a", class_="eTitre")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        francais_tag = columns[1].find("span", class_="infos_small")
        francais = (
            francais_tag.get_text(strip=True).strip("()") if francais_tag else title
        )

        slug_tag = columns[0].find("a")
        slug_href = slug_tag.get("href") if slug_tag else ""
        slug = re.sub(r"\.html$", "", slug_href.split("/")[-1])

        img_tag = columns[0].find("img")
        img_src = img_tag.get("src") if img_tag else ""
        entry_id_match = re.search(r"_(\d+)\.webp", img_src)
        entry_id = int(entry_id_match.group(1)) if entry_id_match else None

        format_value = columns[2].get_text(strip=True)
        status = columns[3].get_text(strip=True)

        data_list.append(
            {
                "title": title,
                "francais": francais,
                "slug": slug,
                "entry_id": entry_id,
                "format": format_value,
                "status": status,
            }
        )

    return data_list


class Nautiljon:
    """Nautiljon class (Optimized and Safer)"""

    def __init__(self, scraper_: Optional[cloudscraper.CloudScraper] = None) -> None:
        """
        Initialize the Nautiljon class with a persistent and resilient session.
        """
        if scraper_ is None:
            self.scraper = cloudscraper.create_scraper()
        else:
            self.scraper = scraper_

        # Strategy: Implement automatic retries with exponential backoff on the scraper session.
        retries = Retry(
            total=5,
            backoff_factor=2,  # A slightly more patient backoff for Cloudflare
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = self.scraper.adapters["https://"]
        adapter.max_retries = retries

        self.base_url = "https://www.nautiljon.com"
        self.search_url = f"{self.base_url}/animes/"
        pprint.print(
            Platform.NAUTILJON,
            Status.READY,
            "Nautiljon anime data scraper ready to use",
        )

    def _get(self, url: str) -> Optional[Response]:
        """
        Get the content of the url using the resilient session.
        """
        try:
            resp = self.scraper.get(url, timeout=20)
            resp.raise_for_status()
            return resp
        except Exception as err:
            pprint.print(
                Platform.NAUTILJON,
                Status.ERR,
                f"Request failed for {url} after retries: {err}",
            )
            return None

    def _scrape_page(self, page_offset: int) -> list[dict[str, Any]]:
        """
        Scrapes a single page of anime data. This is the target for our threads.
        """
        # Strategy: Add a small, random delay to each worker task.
        time.sleep(random.uniform(0.1, 1.5))

        page_url = f"{self.search_url}?dbt={page_offset}"
        response = self._get(page_url)
        if not response:
            return []

        scraped_data = nautiljon_extract_table(response.text)
        if len(scraped_data) < 15 and page_offset > 0:  # Check for incomplete pages
            pg = (page_offset // 15) + 1
            pprint.print(
                Platform.NAUTILJON,
                Status.WARN,
                f"Page {pg} has less than 15 animes, only {len(scraped_data)} animes scraped.",
            )
        return scraped_data

    def get_animes(self) -> list[dict[str, Any]]:
        """
        Get all anime data from Nautiljon concurrently and safely.
        """
        anime_data: list[dict[str, Any]] = []
        pprint.print(
            Platform.NAUTILJON, Status.INFO, "Starting concurrent anime data collection"
        )

        # First, get the last page number sequentially
        first_page = self._get(self.search_url)
        if not first_page:
            raise ConnectionError("Failed to get the first page from Nautiljon.")

        soup = BeautifulSoup(first_page.content, "html.parser")
        last_page_tag = soup.select_one("p.menupage a:last-of-type")
        if not last_page_tag or not last_page_tag.get("href"):
            pprint.print(
                Platform.NAUTILJON,
                Status.ERR,
                "Could not find the last page number on Nautiljon.",
            )
            raise ConnectionError("Failed to read page content")

        last_page_offset = int(last_page_tag["href"].split("=")[-1])
        last_page_num = (last_page_offset // 15) + 1
        pprint.print(
            Platform.NAUTILJON, Status.NOTICE, f"Total pages to scrape: {last_page_num}"
        )

        # Create a list of all page offsets to scrape
        page_offsets = list(range(0, last_page_offset + 15, 15))

        # Strategy: Use a conservative number of workers for a Cloudflare-protected site.
        MAX_WORKERS = 5

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._scrape_page, offset): offset
                for offset in page_offsets
            }

            with alive_bar(
                len(page_offsets), title="Getting Nautiljon data", spinner=None
            ) as bar:
                for future in as_completed(futures):
                    page_results = future.result()
                    if page_results:
                        anime_data.extend(page_results)
                    bar()

        anime_data.sort(key=lambda x: x["title"])

        pprint.print(
            Platform.NAUTILJON,
            Status.PASS,
            f"Done getting animes from Nautiljon. Total animes: {len(anime_data)}",
        )
        return anime_data

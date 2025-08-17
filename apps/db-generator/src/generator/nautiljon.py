# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

# This file is part of 'ids.moe'. It is a derivative work of
# code from the 'animeApi' project by 'nattadasu'. The original license notices
# are preserved in the `NOTICE` file in the root of this repository.

import math
import random
import re
import time
from typing import Optional

import cloudscraper
from alive_progress import alive_bar
from bs4 import BeautifulSoup, Tag
from generator.const import pprint
from generator.prettyprint import Platform, Status
from requests.adapters import Retry
from requests import Response


def nautiljon_extract_table(html_content: str) -> list[dict[str, str | int | None]]:
    """
    Extract the table data from the html content.
    This version is more robust against missing elements and malformed rows.
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

        # Safely extract data with checks to prevent crashes
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
    """Nautiljon class (Robust Sequential Scraper)"""

    def __init__(self, scraper_: Optional[cloudscraper.CloudScraper] = None) -> None:
        """
        Initialize the Nautiljon class with a resilient session.
        """
        if scraper_ is None:
            self.scraper = cloudscraper.create_scraper()
        else:
            self.scraper = scraper_

        # Add a retry strategy for resilience against temporary server errors.
        # This does not add concurrency, it just makes single requests more reliable.
        retries = Retry(
            total=3,
            backoff_factor=1,
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
        Includes a timeout to prevent indefinite hangs.
        """
        try:
            # Using a timeout is critical for robustness
            resp = self.scraper.get(url, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as err:
            # Log the error if all retries fail, and return None
            pprint.print(
                Platform.NAUTILJON, Status.ERR, f"Request failed for {url}: {err}"
            )
            return None

    def get_animes(self) -> list[dict[str, str | int | None]]:
        """
        Get anime data from Nautiljon using the original, reliable sequential method.
        """
        anime_data: list[dict[str, str | int | None]] = []
        pprint.print(
            Platform.NAUTILJON, Status.INFO, "Starting sequential anime data collection"
        )

        # Get the first page to determine the total number of pages
        first_page = self._get(self.search_url)
        if not first_page:
            raise ConnectionError(
                "Failed to get the first page from Nautiljon. Cannot proceed."
            )

        soup = BeautifulSoup(first_page.content, "html.parser")

        # Safer way to find the last page number
        last_page_tag = soup.select_one("p.menupage a:last-of-type")
        if not last_page_tag or not last_page_tag.get("href"):
            raise ValueError("Could not find the last page link on Nautiljon.")

        last_page_offset_str = last_page_tag["href"].split("=")[-1]
        last_page = round(int(last_page_offset_str) / 15)
        pprint.print(Platform.NAUTILJON, Status.NOTICE, f"Last page: {last_page}")

        # The core scraping loop remains sequential, as requested
        with alive_bar(last_page, title="Getting Nautiljon data", spinner=None) as bar:
            scraped = nautiljon_extract_table(first_page.text)
            anime_data.extend(scraped)
            bar()

            for page_number in range(15, last_page * 15, 15):
                # The original, working sleep call is preserved
                time.sleep(random.uniform(0.1, 1.5))

                page = self._get(f"{self.search_url}?dbt={page_number}")
                # If the page failed to download, skip it and continue
                if not page:
                    bar()
                    continue

                scrape = nautiljon_extract_table(page.text)
                if len(scrape) < 15 and page_number < last_page * 15:
                    pg = (page_number // 15) + 1
                    pprint.print(
                        Platform.NAUTILJON,
                        Status.WARN,
                        f"Page {pg} has less than 15 animes, only {len(scrape)} animes scraped",
                    )
                anime_data.extend(scrape)
                bar()

        anime_data.sort(key=lambda x: x["title"])

        pprint.print(
            Platform.NAUTILJON,
            Status.PASS,
            "Done getting animes from Nautiljon,",
            f"total animes: {len(anime_data)},",
            f"or around {math.ceil(len(anime_data) / 15)} pages.",
            f"Expected pages: {last_page}",
        )
        return anime_data

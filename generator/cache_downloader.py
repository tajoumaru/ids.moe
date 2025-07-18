# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Cache-aware downloader for GitHub files and external sources.
Downloads files only when they've changed, maintaining persistent cache.
"""

import os
import requests
import hashlib
import tempfile
import json
import zstandard as zstd
from typing import List, Dict, Optional, Tuple, Protocol
from datetime import datetime, timedelta

from generator.kaize import Kaize
from generator.nautiljon import Nautiljon
from generator.otakotaku import OtakOtaku
from generator.const import pprint
from generator.prettyprint import Platform, Status


class DatabaseConnection(Protocol):
    """Protocol for database connection compatibility."""

    def cursor(self):
        """Return a cursor object."""
        ...

    def commit(self) -> None:
        """Commit the transaction."""
        ...


class DatabaseCursor(Protocol):
    """Protocol for database cursor compatibility."""

    def execute(self, query: str, params: Optional[Tuple] = None) -> None:
        """Execute a query with optional parameters."""
        ...

    def fetchone(self) -> Optional[Tuple]:
        """Fetch one row from the result set."""
        ...

    def fetchall(self) -> List[Tuple]:
        """Fetch all rows from the result set."""
        ...


class CacheDownloader:
    """Handles intelligent file caching with hash-based skip logic."""

    def __init__(self, connection: DatabaseConnection, cache_dir: str = "src/cache"):
        self.connection = connection
        self.cache_dir = cache_dir

        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)

        # GitHub API configuration
        from generator.const import GITHUB_TOKEN

        self.github_token = GITHUB_TOKEN
        self.github_headers = {}
        if self.github_token:
            self.github_headers["Authorization"] = f"token {self.github_token}"

    def download_all_files(self) -> Tuple[List[str], List[str]]:
        """Download all files from GitHub and run scrapers."""
        github_files = self.download_github_files()
        scraper_files = self.run_scrapers()

        return github_files, scraper_files

    def download_github_files(self, ignore_cache: bool = False) -> List[str]:
        """Download all GitHub-hosted files using GitHub SHA for change detection.

        Args:
            ignore_cache: If True, ignore cache and re-download all files
        """
        github_files = {
            # Manual mapping files
            "kaize_manual.json": "https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/raw/kaize_manual.json",
            "otakotaku_manual.json": "https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/raw/otakotaku_manual.json",
            "silveryasha_manual.json": "https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/raw/silveryasha_manual.json",
            # Data source files
            "arm.json": "https://raw.githubusercontent.com/kawaiioverflow/arm/master/arm.json",
            "anitrakt_tv.json": "https://raw.githubusercontent.com/rensetsu/db.trakt.anitrakt/main/db/tv.json",
            "anitrakt_movie.json": "https://raw.githubusercontent.com/rensetsu/db.trakt.anitrakt/main/db/movies.json",
            "silveryasha.json": "https://raw.githubusercontent.com/rensetsu/db.rensetsu.public-dump/main/Silveryasha/silveryasha_raw.json",
            "fribb_animelists.json": "https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-lists-reduced.json",
        }

        downloaded_files = []

        pprint.print(Platform.SYSTEM, Status.INFO, "Downloading GitHub-hosted files...")
        for filename, url in github_files.items():
            try:
                # Convert raw URL to API URL for SHA checking
                api_url = self._get_github_api_url(url)
                if api_url:
                    current_sha = self._get_github_file_sha(api_url)

                    if not current_sha:
                        pprint.print(
                            Platform.SYSTEM,
                            Status.WARN,
                            f"Could not get SHA for {filename}, downloading anyway",
                        )
                        should_download = True
                    else:
                        should_download = (
                            ignore_cache
                            or self._should_download_github_file(url, current_sha)
                        )
                else:
                    # Not a GitHub URL, download anyway
                    should_download = True
                    current_sha = None

                if should_download:
                    file_path = os.path.join(self.cache_dir, filename)

                    # Download file
                    response = requests.get(
                        url, headers=self.github_headers if api_url else {}, timeout=30
                    )
                    response.raise_for_status()

                    # Save to cache
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(response.text)

                    # Update cache record
                    self._update_download_cache(
                        url,
                        file_path,
                        current_sha or self._compute_file_hash(file_path),
                        "github",
                    )
                    downloaded_files.append(file_path)

                    pprint.print(Platform.SYSTEM, Status.PASS, f"Downloaded {filename}")
                else:
                    pprint.print(
                        Platform.SYSTEM, Status.INFO, f"Skipping {filename} (unchanged)"
                    )

            except Exception as e:
                pprint.print(
                    Platform.SYSTEM, Status.ERR, f"Error downloading {filename}: {e}"
                )
                continue

        # Handle AOD separately (GitHub releases with zstd)
        aod_file = self._download_aod()
        if aod_file:
            downloaded_files.append(aod_file)

        return downloaded_files

    def _download_aod(self) -> Optional[str]:
        """Download AOD from GitHub releases with special handling."""
        url = "https://github.com/manami-project/anime-offline-database/releases/download/latest/anime-offline-database-minified.json.zst"
        filename = "aod.json"

        try:
            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Downloading {filename} from GitHub releases...",
            )

            # For GitHub releases, we can't use SHA easily, so check ETag or Last-Modified
            file_path = os.path.join(self.cache_dir, filename)

            # Get current cache info
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT file_hash, metadata FROM download_cache 
                WHERE source_url = ? AND source_type = 'github_release'
            """,
                (url,),
            )
            cache_info = cursor.fetchone()

            # Make HEAD request to check if file changed
            head_response = requests.head(url, allow_redirects=True)
            etag = head_response.headers.get("ETag", "")
            last_modified = head_response.headers.get("Last-Modified", "")

            # Check if we should download
            should_download = True
            if cache_info and cache_info[1]:
                try:
                    metadata = json.loads(cache_info[1])
                    if (
                        metadata.get("etag") == etag
                        or metadata.get("last_modified") == last_modified
                    ):
                        should_download = False
                except Exception:
                    pass

            if not should_download:
                pprint.print(
                    Platform.SYSTEM, Status.INFO, f"Skipping {filename} (unchanged)"
                )
                return None

            # Download to temporary location
            with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as temp_file:
                response = requests.get(url, timeout=120)
                response.raise_for_status()
                temp_file.write(response.content)
                temp_path = temp_file.name

            # Decompress zstd file
            with open(temp_path, "rb") as f:
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(f) as reader:
                    decompressed = reader.read()

            # Save decompressed JSON
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(decompressed.decode("utf-8"))

            # Clean up temp file
            os.unlink(temp_path)

            # Compute hash and update cache with metadata
            file_hash = self._compute_file_hash(file_path)
            metadata = json.dumps({"etag": etag, "last_modified": last_modified})

            cursor.execute("DELETE FROM download_cache WHERE source_url = ?", (url,))
            cursor.execute(
                """
                INSERT INTO download_cache (source_type, source_url, file_path, file_hash, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("github_release", url, file_path, file_hash, metadata),
            )
            self.connection.commit()

            pprint.print(Platform.SYSTEM, Status.PASS, f"Downloaded {filename}")
            return file_path

        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.ERR, f"Error downloading {filename}: {e}"
            )
            return None

    def run_scrapers(self, ignore_cache: bool = False) -> List[str]:
        """Run scrapers for Kaize, Nautiljon, and Otak Otaku.

        Args:
            ignore_cache: If True, ignore cache expiry and re-run all scrapers
        """
        scraped_files = []

        pprint.print(
            Platform.SYSTEM, Status.INFO, "Checking scrapers for external data..."
        )

        # Check each scraper individually
        scrapers_to_run = []

        if ignore_cache or self._should_run_scraper("kaize"):
            scrapers_to_run.append("kaize")
        else:
            pprint.print(
                Platform.KAIZE, Status.INFO, "Skipping scraper (rate limit not expired)"
            )

        if ignore_cache or self._should_run_scraper("nautiljon"):
            scrapers_to_run.append("nautiljon")
        else:
            pprint.print(
                Platform.NAUTILJON,
                Status.INFO,
                "Skipping scraper (rate limit not expired)",
            )

        if ignore_cache or self._should_run_scraper("otakotaku"):
            scrapers_to_run.append("otakotaku")
        else:
            pprint.print(
                Platform.OTAKOTAKU,
                Status.INFO,
                "Skipping scraper (rate limit not expired)",
            )

        if not scrapers_to_run:
            pprint.print(Platform.SYSTEM, Status.INFO, "No scrapers need to run")
            return scraped_files

        pprint.print(
            Platform.SYSTEM,
            Status.INFO,
            f"Running scrapers: {', '.join(scrapers_to_run)}",
        )

        # Run only the scrapers that need to run
        if "kaize" in scrapers_to_run:
            kaize_file = self._run_kaize_scraper()
            if kaize_file:
                scraped_files.append(kaize_file)

        if "nautiljon" in scrapers_to_run:
            nautiljon_file = self._run_nautiljon_scraper()
            if nautiljon_file:
                scraped_files.append(nautiljon_file)

        if "otakotaku" in scrapers_to_run:
            otakotaku_file = self._run_otakotaku_scraper()
            if otakotaku_file:
                scraped_files.append(otakotaku_file)

        return scraped_files

    def get_all_cache_files(self) -> Dict[str, str]:
        """Get all cached files."""
        cache_files = {}

        # Get all JSON files in cache directory
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                cache_files[filename] = os.path.join(self.cache_dir, filename)

        return cache_files

    def _get_github_api_url(self, raw_url: str) -> Optional[str]:
        """Convert GitHub raw URL to API URL."""
        # Example: https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/raw/kaize_manual.json
        # Needs to become: https://api.github.com/repos/nattadasu/animeApi/contents/database/raw/kaize_manual.json?ref=v3

        if "raw.githubusercontent.com" not in raw_url:
            return None

        try:
            # Parse the URL parts
            # Remove the protocol and domain
            path = raw_url.replace("https://raw.githubusercontent.com/", "")

            # Split by / to get components
            parts = path.split("/", 3)  # Split into max 4 parts

            if len(parts) < 4:
                return None

            account = parts[0]
            repo = parts[1]
            branch = parts[2]
            filepath = parts[3]

            # Construct the API URL
            api_url = f"https://api.github.com/repos/{account}/{repo}/contents/{filepath}?ref={branch}"

            return api_url

        except Exception:
            return None

    def _get_github_file_sha(self, api_url: str) -> Optional[str]:
        """Get SHA hash of a file from GitHub API."""
        try:
            response = requests.get(api_url, headers=self.github_headers, timeout=10)
            response.raise_for_status()
            return response.json().get("sha")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error getting GitHub SHA: {e}")
            return None

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _should_download_github_file(self, url: str, current_sha: str) -> bool:
        """Check if GitHub file should be downloaded based on SHA."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT file_hash FROM download_cache 
            WHERE source_url = ? AND source_type = 'github'
        """,
            (url,),
        )

        result = cursor.fetchone()
        return result is None or result[0] != current_sha

    def _update_download_cache(
        self, url: str, file_path: str, file_hash: str, source_type: str
    ) -> None:
        """Update download cache with new file information."""
        cursor = self.connection.cursor()

        # Set expiry for rate-limited sources
        expires_at = None
        if source_type == "scraper":
            expires_at = (datetime.now() + timedelta(days=14)).isoformat()

        # Delete existing record if present
        cursor.execute("DELETE FROM download_cache WHERE source_url = ?", (url,))

        # Insert new record
        cursor.execute(
            """
            INSERT INTO download_cache (source_type, source_url, file_path, file_hash, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (source_type, url, file_path, file_hash, expires_at),
        )

        self.connection.commit()

    def clean_expired_cache(self) -> None:
        """Remove expired cache entries."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            DELETE FROM download_cache 
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """,
            (datetime.now().isoformat(),),
        )
        self.connection.commit()

    def _should_run_scraper(self, scraper_name: str) -> bool:
        """Check if a specific scraper should run based on rate limiting."""
        cursor = self.connection.cursor()

        url = f"scraper://{scraper_name}"
        cursor.execute(
            """
            SELECT expires_at FROM download_cache 
            WHERE source_url = ? AND source_type = 'scraper'
        """,
            (url,),
        )

        result = cursor.fetchone()
        if result is None:
            pprint.print(
                Platform.SYSTEM, Status.INFO, f"No cache entry for {scraper_name}"
            )
            return True  # No cache entry, should run

        expires_at = result[0]
        if expires_at:
            expiry_time = datetime.fromisoformat(expires_at)
            if datetime.now() > expiry_time:
                pprint.print(
                    Platform.SYSTEM, Status.INFO, f"Cache expired for {scraper_name}"
                )
                return True  # Cache expired, should run

        return False  # Cache is still valid

    def _run_kaize_scraper(self) -> Optional[str]:
        """Run Kaize scraper and save data."""
        pprint.print(Platform.KAIZE, Status.INFO, "Running scraper...")

        # Get credentials from constants
        from generator.const import (
            KAIZE_SESSION,
            KAIZE_XSRF_TOKEN,
            KAIZE_EMAIL,
            KAIZE_PASSWORD,
        )

        session = KAIZE_SESSION
        xsrf_token = KAIZE_XSRF_TOKEN
        email = KAIZE_EMAIL
        password = KAIZE_PASSWORD

        if not all([session, xsrf_token, email, password]):
            pprint.print(
                Platform.KAIZE,
                Status.WARN,
                "Credentials not found in environment, skipping",
            )
            return None

        try:
            # Initialize and run scraper
            kaize = Kaize(
                kaize_session=session,  # type: ignore
                xsrf_token=xsrf_token,  # type: ignore
            )

            # Get data
            data = kaize.get_anime()

            # Save to cache
            file_path = os.path.join(self.cache_dir, "kaize.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Compute hash and update cache
            file_hash = self._compute_file_hash(file_path)
            self._update_download_cache(
                "scraper://kaize", file_path, file_hash, "scraper"
            )

            pprint.print(Platform.KAIZE, Status.PASS, "Data scraped successfully")
            return file_path

        except Exception as e:
            pprint.print(Platform.KAIZE, Status.ERR, f"Error running scraper: {e}")
            return None

    def _run_nautiljon_scraper(self) -> Optional[str]:
        """Run Nautiljon scraper and save data."""
        pprint.print(Platform.NAUTILJON, Status.INFO, "Running scraper...")

        try:
            # Initialize and run scraper
            nautiljon = Nautiljon()

            # Get data
            data = nautiljon.get_animes()

            # Save to cache
            file_path = os.path.join(self.cache_dir, "nautiljon.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Compute hash and update cache
            file_hash = self._compute_file_hash(file_path)
            self._update_download_cache(
                "scraper://nautiljon", file_path, file_hash, "scraper"
            )

            pprint.print(Platform.NAUTILJON, Status.PASS, "Data scraped successfully")
            return file_path

        except Exception as e:
            pprint.print(Platform.NAUTILJON, Status.ERR, f"Error running scraper: {e}")
            return None

    def _run_otakotaku_scraper(self) -> Optional[str]:
        """Run Otak Otaku scraper and save data."""
        pprint.print(Platform.OTAKOTAKU, Status.INFO, "Running scraper...")

        try:
            # Initialize and run scraper
            otakotaku = OtakOtaku()

            # Get data
            data = otakotaku.get_anime()

            # Save to cache
            file_path = os.path.join(self.cache_dir, "otakotaku.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Compute hash and update cache
            file_hash = self._compute_file_hash(file_path)
            self._update_download_cache(
                "scraper://otakotaku", file_path, file_hash, "scraper"
            )

            pprint.print(Platform.OTAKOTAKU, Status.PASS, "Data scraped successfully")
            return file_path

        except Exception as e:
            pprint.print(Platform.OTAKOTAKU, Status.ERR, f"Error running scraper: {e}")
            return None


# Compatibility functions for pipeline
def download_github_files(
    connection: DatabaseConnection, cache_dir: str = "src/cache"
) -> List[str]:
    """Download GitHub files and return list of downloaded file paths."""
    downloader = CacheDownloader(connection, cache_dir)
    return downloader.download_github_files()


def download_external_files(
    connection: DatabaseConnection, cache_dir: str = "src/cache"
) -> List[str]:
    """Run scrapers and return list of scraped file paths."""
    downloader = CacheDownloader(connection, cache_dir)
    return downloader.run_scrapers()

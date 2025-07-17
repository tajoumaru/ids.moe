"""
Data extractor for parsing JSON files and extracting structured data.
Parses JSON files and extracts individual fields for database storage.
"""

import json
import os
from typing import List, Dict, Optional

from generator.const import pprint
from generator.prettyprint import Platform, Status
from generator.anime_record import AnimeRecord


class DataExtractor:
    """Extracts structured data from JSON files."""

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = cache_dir
        self.platform_field_mapping = {
            "animenewsnetwork": "animenewsnetwork",
            "animeplanet": "animeplanet",
            "anisearch": "anisearch",
            "annict": "annict",
            "imdb": "imdb",
            "livechart": "livechart",
            "notify": "notify",
            "otakotaku": "otakotaku",
            "shikimori": "shikimori",
            "shoboi": "shoboi",
            "silveryasha": "silveryasha",
            "simkl": "simkl",
            "themoviedb": "themoviedb",
        }

    def extract_anime_data(self, cache_files: Dict[str, str]) -> List[AnimeRecord]:
        """Extract anime data from all cached files."""
        pprint.print(
            Platform.SYSTEM, Status.INFO, "Extracting anime data from cached files..."
        )

        # Start with AOD data as the base
        aod_data = self._load_aod_data(cache_files.get("aod.json"))
        if not aod_data:
            pprint.print(
                Platform.ANIMEOFFLINEDATABASE,
                Status.ERR,
                "No AOD data found, cannot proceed",
            )
            return []

        # Convert AOD data to AnimeRecord objects
        records = []
        for entry in aod_data:
            record = self._create_base_record(entry)
            if record:
                records.append(record)

        # Use DataMatcher for comprehensive data matching
        if self.cache_dir:
            from generator.data_matcher import DataMatcher

            matcher = DataMatcher(self.cache_dir)
            records = matcher.enhance_records(records)
        else:
            # Fallback to simple platform data enhancement
            self._enhance_with_platform_data(records, cache_files)

        # Compute hashes for all records
        for record in records:
            record.data_hash = record.compute_hash()

        pprint.print(
            Platform.SYSTEM, Status.PASS, f"Extracted {len(records)} anime records"
        )
        return records

    def _load_aod_data(self, aod_file: Optional[str]) -> List[Dict]:
        """Load anime offline database data."""
        if not aod_file or not os.path.exists(aod_file):
            return []

        try:
            with open(aod_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # AOD structure: {"data": [...]}
            return data.get("data", [])
        except Exception as e:
            pprint.print(
                Platform.ANIMEOFFLINEDATABASE,
                Status.ERR,
                f"Error loading AOD data: {e}",
            )
            return []

    def _create_base_record(self, entry: Dict) -> Optional[AnimeRecord]:
        """Create base AnimeRecord from AOD entry."""
        try:
            # Extract title
            title = entry.get("title")
            if not title:
                return None

            # Create record with basic fields
            record = AnimeRecord(title=title)

            # Extract platform IDs from sources using the same logic as legacy simplify_aod_data
            sources = entry.get("sources", [])
            for source in sources:
                if source.startswith("https://anidb.net/anime/"):
                    record.anidb = self._extract_id_from_url(source)
                elif source.startswith("https://anilist.co/anime/"):
                    record.anilist = self._extract_id_from_url(source)
                elif source.startswith("https://anime-planet.com/anime/"):
                    record.animeplanet = source.split("/")[-1]  # Extract slug, not ID
                elif source.startswith("https://anisearch.com/anime/"):
                    record.anisearch = self._extract_id_from_url(source)
                elif source.startswith("https://kitsu.io/anime/") or source.startswith(
                    "https://kitsu.app/anime/"
                ):
                    record.kitsu = self._extract_id_from_url(source)
                elif source.startswith("https://livechart.me/anime/"):
                    record.livechart = self._extract_id_from_url(source)
                elif source.startswith("https://myanimelist.net/anime/"):
                    record.myanimelist = self._extract_id_from_url(source)
                elif source.startswith("https://notify.moe/anime/"):
                    record.notify = source.split("/")[
                        -1
                    ]  # Extract base64 string, not ID
                elif source.startswith("https://simkl.com/anime/"):
                    record.simkl = self._extract_id_from_url(source)
                elif source.startswith("https://animenewsnetwork.com/"):
                    # Extract ID from URL parameter: https://animenewsnetwork.com/encyclopedia/anime.php?id=25117
                    if "id=" in source:
                        record.animenewsnetwork = int(source.split("id=")[-1])

            # Set shikimori to same as myanimelist (they use the same IDs)
            if record.myanimelist:
                record.shikimori = record.myanimelist

            return record
        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.ERR, f"Error creating base record: {e}"
            )
            return None

    def _enhance_with_platform_data(
        self, records: List[AnimeRecord], cache_files: Dict[str, str]
    ) -> None:
        """Enhance records with data from platform-specific files."""
        # Create lookup by MAL ID for fast matching
        mal_lookup = {}
        for i, record in enumerate(records):
            if record.myanimelist:
                mal_lookup[record.myanimelist] = i

        # Process each platform file
        for filename, file_path in cache_files.items():
            if filename == "aod.json":
                continue  # Already processed

            platform_data = self._load_platform_data(file_path, filename)
            if not platform_data:
                continue

            self._merge_platform_data(records, mal_lookup, platform_data, filename)

    def _load_platform_data(self, file_path: str, filename: str) -> List[Dict]:
        """Load platform-specific data file."""
        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle different file structures
            if filename == "arm.json":
                return data  # Direct array
            elif filename in ["anitrakt.json", "fribb_animelists.json"]:
                return data  # Direct array
            elif filename.endswith("_manual.json"):
                # Manual mappings: {"title": "platform_id"}
                return [{"title": k, "platform_id": v} for k, v in data.items()]
            else:
                # Default structure
                return data if isinstance(data, list) else []

        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error loading {filename}: {e}")
            return []

    def _merge_platform_data(
        self,
        records: List[AnimeRecord],
        mal_lookup: Dict[int, int],
        platform_data: List[Dict],
        filename: str,
    ) -> None:
        """Merge platform-specific data into records."""
        platform_name = self._get_platform_name(filename)
        if not platform_name:
            return

        merged_count = 0

        for entry in platform_data:
            # Find matching record by MAL ID
            mal_id = entry.get("mal_id") or entry.get("myanimelist")
            if not mal_id:
                continue

            record_index = mal_lookup.get(int(mal_id))
            if record_index is None:
                continue

            record = records[record_index]

            # Merge platform-specific data
            if platform_name == "kaize":
                record.kaize = entry.get("kaize")
                record.kaize_id = entry.get("kaize_id")
            elif platform_name == "nautiljon":
                record.nautiljon = entry.get("nautiljon")
                record.nautiljon_id = entry.get("nautiljon_id")
            elif platform_name == "trakt":
                record.trakt = entry.get("trakt")
                record.trakt_type = entry.get("trakt_type")
                record.trakt_season = entry.get("trakt_season")
            elif platform_name == "themoviedb":
                # TheMovieDB is always formatted as movie
                record.themoviedb = entry.get("themoviedb")
            elif platform_name in self.platform_field_mapping:
                # Simple platform ID mapping
                field_name = self.platform_field_mapping[platform_name]
                platform_id = entry.get(platform_name)
                if platform_id:
                    setattr(record, field_name, platform_id)

            merged_count += 1

        if merged_count > 0:
            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Merged {merged_count} records with {platform_name} data",
            )

    def _get_platform_name(self, filename: str) -> Optional[str]:
        """Get platform name from filename."""
        if filename == "kaize.json":
            return "kaize"
        elif filename == "nautiljon.json":
            return "nautiljon"
        elif filename == "otakotaku.json":
            return "otakotaku"
        elif filename == "silveryasha.json":
            return "silveryasha"
        elif filename == "anitrakt.json":
            return "trakt"
        elif filename == "fribb_animelists.json":
            return "animenewsnetwork"  # Fribb contains ANN data
        elif filename == "arm.json":
            return "arm"  # ARM contains multiple platforms
        else:
            # Try to extract from filename
            base_name = filename.replace(".json", "").replace("_manual", "")
            if base_name in self.platform_field_mapping:
                return base_name
            return None

    def _extract_id_from_url(self, url: str) -> Optional[int]:
        """Extract numeric ID from URL."""
        try:
            # Find the last numeric part in the URL
            parts = url.split("/")
            for part in reversed(parts):
                if part.isdigit():
                    return int(part)
            return None
        except Exception:
            return None


def extract_anime_data(
    cache_files: Dict[str, str], cache_dir: str | None = None
) -> List[AnimeRecord]:
    """Extract anime data from cached files."""
    extractor = DataExtractor(cache_dir)
    return extractor.extract_anime_data(cache_files)

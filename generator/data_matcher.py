"""
Data matcher module that implements the combiner/converter functionality.
Handles fuzzy matching, cross-platform ID linking, and manual mappings.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from multiprocessing import Pool, cpu_count
from dataclasses import asdict

from fuzzywuzzy import fuzz
from slugify import slugify

from generator.const import pprint
from generator.prettyprint import Platform, Status
from generator.anime_record import AnimeRecord


class DataMatcher:
    """Matches and combines anime data from multiple sources."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.platform_data = {}
        self.manual_mappings = {}

    def enhance_records(self, records: List[AnimeRecord]) -> List[AnimeRecord]:
        """Enhance records with matched data from all platforms."""
        pprint.print(
            Platform.SYSTEM, Status.INFO, "Starting data matching and enhancement..."
        )

        # Load all platform data and manual mappings
        self._load_platform_data()
        self._load_manual_mappings()

        # Create lookup indexes
        mal_lookup = {r.myanimelist: r for r in records if r.myanimelist}
        anilist_lookup = {r.anilist: r for r in records if r.anilist}
        anidb_lookup = {r.anidb: r for r in records if r.anidb}
        title_lookup = {r.title: r for r in records}

        # Phase 1: Combine data using direct ID matches
        self._combine_arm_data(records, mal_lookup, anilist_lookup)
        self._combine_anitrakt_data(records, mal_lookup)
        self._combine_fribb_data(records, anidb_lookup)

        # Phase 2: Link data using fuzzy matching
        self._link_kaize_data(records, title_lookup)
        self._link_nautiljon_data(records, title_lookup)
        self._link_otakotaku_data(records, title_lookup)
        self._link_silveryasha_data(records, mal_lookup, title_lookup)

        # Phase 3: Apply manual mappings
        self._apply_manual_mappings(records, title_lookup)

        pprint.print(Platform.SYSTEM, Status.PASS, f"Enhanced {len(records)} records")
        return records

    def _load_platform_data(self):
        """Load all platform data files."""
        platform_files = {
            "arm": "arm.json",
            "anitrakt": "anitrakt_tv.json",  # Use TV data by default
            "fribb": "fribb_animelists.json",
            "kaize": "kaize.json",
            "nautiljon": "nautiljon.json",
            "otakotaku": "otakotaku.json",
            "silveryasha": "silveryasha.json",
        }

        for platform, filename in platform_files.items():
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                        # Handle different JSON structures
                        if platform == "silveryasha":
                            # SilverYasha has structure: {"data": [...]}
                            if isinstance(raw_data, dict) and "data" in raw_data:
                                self.platform_data[platform] = raw_data["data"]
                            else:
                                pprint.print(
                                    Platform.SYSTEM,
                                    Status.ERR,
                                    f"DEBUG: SilverYasha unexpected structure: {type(raw_data)}",
                                )
                                self.platform_data[platform] = []
                        else:
                            # Other platforms should be direct arrays
                            if isinstance(raw_data, list):
                                self.platform_data[platform] = raw_data
                            else:
                                pprint.print(
                                    Platform.SYSTEM,
                                    Status.ERR,
                                    f"DEBUG: {platform} unexpected structure: {type(raw_data)}",
                                )
                                self.platform_data[platform] = []

                        pprint.print(
                            Platform.SYSTEM,
                            Status.INFO,
                            f"Loaded {len(self.platform_data[platform])} items from {filename}",
                        )
                except Exception as e:
                    pprint.print(
                        Platform.SYSTEM, Status.ERR, f"Error loading {filename}: {e}"
                    )
                    self.platform_data[platform] = []
            else:
                self.platform_data[platform] = []

    def _load_manual_mappings(self):
        """Load manual mapping files."""
        manual_files = [
            "kaize_manual.json",
            "otakotaku_manual.json",
            "silveryasha_manual.json",
        ]

        for filename in manual_files:
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        platform = filename.replace("_manual.json", "")
                        self.manual_mappings[platform] = json.load(f)
                except Exception as e:
                    pprint.print(
                        Platform.SYSTEM, Status.ERR, f"Error loading {filename}: {e}"
                    )

    def _combine_arm_data(
        self, records: List[AnimeRecord], mal_lookup: Dict, anilist_lookup: Dict
    ):
        """Combine ARM data (contains Shoboi and Annict IDs)."""
        arm_data = self.platform_data.get("arm", [])
        if not arm_data:
            return

        # Create ARM lookups
        arm_by_mal = {item["mal_id"]: item for item in arm_data if item.get("mal_id")}
        arm_by_anilist = {
            item["anilist_id"]: item for item in arm_data if item.get("anilist_id")
        }

        linked = 0
        for record in records:
            arm_item = None

            # Try MAL ID first
            if record.myanimelist and record.myanimelist in arm_by_mal:
                arm_item = arm_by_mal[record.myanimelist]
            # Then try AniList ID
            elif record.anilist and record.anilist in arm_by_anilist:
                arm_item = arm_by_anilist[record.anilist]
                # Also update MAL ID if missing
                if not record.myanimelist and arm_item.get("mal_id"):
                    record.myanimelist = arm_item["mal_id"]

            if arm_item:
                record.shoboi = arm_item.get("syobocal_tid")
                record.annict = arm_item.get("annict_id")
                # Update AniList if missing
                if not record.anilist and arm_item.get("anilist_id"):
                    record.anilist = arm_item["anilist_id"]
                linked += 1

        pprint.print(
            Platform.ARM, Status.PASS, f"Linked {linked} records with ARM data"
        )

    def _combine_anitrakt_data(self, records: List[AnimeRecord], mal_lookup: Dict):
        """Combine AniTrakt data (Trakt IDs)."""
        anitrakt_data = self.platform_data.get("anitrakt", [])
        if not anitrakt_data:
            return

        # Create lookup by MAL ID
        anitrakt_by_mal = {
            item["mal_id"]: item for item in anitrakt_data if item.get("mal_id")
        }

        linked = 0
        for record in records:
            if record.myanimelist and record.myanimelist in anitrakt_by_mal:
                item = anitrakt_by_mal[record.myanimelist]
                record.trakt = item.get("trakt_id")
                record.trakt_type = item.get("type")
                record.trakt_season = item.get("season")
                linked += 1

        pprint.print(
            Platform.ANITRAKT,
            Status.PASS,
            f"Linked {linked} records with AniTrakt data",
        )

    def _combine_fribb_data(self, records: List[AnimeRecord], anidb_lookup: Dict):
        """Combine Fribb's Animelists data (IMDB and TMDB IDs via AniDB)."""
        fribb_data = self.platform_data.get("fribb", [])
        if not fribb_data:
            return

        # Create lookup by AniDB ID
        fribb_by_anidb = {
            item["anidb_id"]: item for item in fribb_data if item.get("anidb_id")
        }

        linked = 0
        for record in records:
            if record.anidb and record.anidb in fribb_by_anidb:
                item = fribb_by_anidb[record.anidb]
                record.imdb = item.get("imdb_id")

                # Handle TMDB ID (may be comma-separated)
                tmdb = item.get("themoviedb_id")
                if isinstance(tmdb, str) and "," in tmdb:
                    tmdb = int(tmdb.split(",")[0])
                elif tmdb:
                    tmdb = int(tmdb)
                record.themoviedb = tmdb
                linked += 1

        pprint.print(
            Platform.FRIBB, Status.PASS, f"Linked {linked} records with Fribb data"
        )

    def _link_kaize_data(self, records: List[AnimeRecord], title_lookup: Dict):
        """Link Kaize data using fuzzy matching."""
        kaize_data = self.platform_data.get("kaize", [])
        if not kaize_data:
            return

        # Create slug lookup for exact matches
        aod_by_slug = {}
        for record in records:
            slug = slugify(record.title).replace("-", "")
            aod_by_slug[slug] = record

        kaize_by_slug = {}
        for item in kaize_data:
            slug = slugify(item["slug"]).replace("-", "")
            kaize_by_slug[slug] = item

        linked = 0
        unlinked = []

        # First pass: exact slug matches
        for kz_slug, kz_item in kaize_by_slug.items():
            if kz_slug in aod_by_slug:
                record = aod_by_slug[kz_slug]
                record.kaize = kz_item["slug"]
                record.kaize_id = kz_item["kaize"] if kz_item["kaize"] != 0 else None
                linked += 1
            else:
                unlinked.append(kz_item)

        # Second pass: fuzzy matching for unlinked items
        if unlinked:
            pprint.print(
                Platform.KAIZE,
                Status.INFO,
                f"Fuzzy matching {len(unlinked)} unlinked items",
            )
            matches = self._fuzzy_match_parallel(unlinked, records, threshold=85)

            for kz_item, record in matches:
                record.kaize = kz_item["slug"]
                record.kaize_id = kz_item["kaize"] if kz_item["kaize"] != 0 else None
                linked += 1

        pprint.print(
            Platform.KAIZE, Status.PASS, f"Linked {linked} records with Kaize data"
        )

    def _link_nautiljon_data(self, records: List[AnimeRecord], title_lookup: Dict):
        """Link Nautiljon data using title matching."""
        nautiljon_data = self.platform_data.get("nautiljon", [])
        if not nautiljon_data:
            return

        # Create title lookup for Nautiljon
        nautiljon_by_title = {item["title"]: item for item in nautiljon_data}

        linked = 0
        unlinked = []

        # First pass: exact title matches
        for nj_title, nj_item in nautiljon_by_title.items():
            if nj_title in title_lookup:
                record = title_lookup[nj_title]
                record.nautiljon = nj_item["slug"]
                record.nautiljon_id = nj_item["entry_id"]
                linked += 1
            else:
                unlinked.append(nj_item)

        # Second pass: fuzzy matching
        if unlinked:
            pprint.print(
                Platform.NAUTILJON,
                Status.INFO,
                f"Fuzzy matching {len(unlinked)} unlinked items",
            )
            matches = self._fuzzy_match_parallel(unlinked, records, threshold=90)

            for nj_item, record in matches:
                record.nautiljon = nj_item["slug"]
                record.nautiljon_id = nj_item["entry_id"]
                linked += 1

        pprint.print(
            Platform.NAUTILJON,
            Status.PASS,
            f"Linked {linked} records with Nautiljon data",
        )

    def _link_otakotaku_data(self, records: List[AnimeRecord], title_lookup: Dict):
        """Link Otak Otaku data using title matching."""
        otakotaku_data = self.platform_data.get("otakotaku", [])
        if not otakotaku_data:
            return

        # Create title lookup
        ot_by_title = {item["title"]: item for item in otakotaku_data}

        linked = 0
        unlinked = []

        # First pass: exact title matches
        for ot_title, ot_item in ot_by_title.items():
            if ot_title in title_lookup:
                record = title_lookup[ot_title]
                record.otakotaku = ot_item["otakotaku"]
                linked += 1
            else:
                unlinked.append(ot_item)

        # Second pass: fuzzy matching with title preprocessing
        if unlinked:
            pprint.print(
                Platform.OTAKOTAKU,
                Status.INFO,
                f"Fuzzy matching {len(unlinked)} unlinked items",
            )
            matches = self._fuzzy_match_parallel(
                unlinked,
                records,
                threshold=90,
                title_preprocessor=self._otakotaku_title_preprocessor,
            )

            for ot_item, record in matches:
                record.otakotaku = ot_item["otakotaku"]
                linked += 1

        pprint.print(
            Platform.OTAKOTAKU,
            Status.PASS,
            f"Linked {linked} records with Otak Otaku data",
        )

    def _link_silveryasha_data(
        self, records: List[AnimeRecord], mal_lookup: Dict, title_lookup: Dict
    ):
        """Link SilverYasha data using MAL ID or title matching."""
        silveryasha_data = self.platform_data.get("silveryasha", [])
        if not silveryasha_data:
            return


        linked = 0
        unlinked = []

        # Process each SilverYasha item
        for sy_item in silveryasha_data:
            mal_id = sy_item.get("mal_id")
            matched = False

            # Try MAL ID match first
            if mal_id:
                mal_id_int = int(mal_id)
                if mal_id_int in mal_lookup:
                    record = mal_lookup[mal_id_int]
                    record.silveryasha = sy_item["id"]
                    linked += 1
                    matched = True
            # Try title match
            elif sy_item["title"] in title_lookup:
                record = title_lookup[sy_item["title"]]
                record.silveryasha = sy_item["id"]
                linked += 1
                matched = True

            if not matched:
                unlinked.append(sy_item)

        # Fuzzy match unlinked items
        if unlinked:
            pprint.print(
                Platform.SILVERYASHA,
                Status.INFO,
                f"Starting fuzzy matching for {len(unlinked)} unlinked items",
            )
            matches = self._fuzzy_match_parallel(
                unlinked, records, threshold=95
            )


            for sy_item, record in matches:
                record.silveryasha = sy_item["id"]
                linked += 1

        pprint.print(
            Platform.SILVERYASHA,
            Status.PASS,
            f"Linked {linked} records with SilverYasha data",
        )

    def _apply_manual_mappings(self, records: List[AnimeRecord], title_lookup: Dict):
        """Apply manual mappings from JSON files."""
        for platform, mappings in self.manual_mappings.items():
            applied = 0

            for title, platform_data in mappings.items():
                try:
                    # Handle list format (override flag)
                    if isinstance(platform_data, list):
                        platform_data = platform_data[0]

                    if title in title_lookup:
                        record = title_lookup[title]

                        if platform == "kaize":
                            # Kaize manual format: {"kaize": "slug", "kaize_id": id}
                            if isinstance(platform_data, dict):
                                record.kaize = platform_data.get("kaize")
                                record.kaize_id = platform_data.get("kaize_id")
                            else:
                                record.kaize = platform_data
                        elif platform == "otakotaku":
                            # Otakotaku manual format: just the ID
                            record.otakotaku = platform_data
                        elif platform == "silveryasha":
                            # SilverYasha manual format: just the ID
                            record.silveryasha = platform_data

                        applied += 1

                except Exception as e:
                    pprint.print(
                        Platform.SYSTEM,
                        Status.ERR,
                        f"Error processing {platform} manual mapping: title='{title}', data={platform_data}, error={e}",
                    )
                    raise

            if applied > 0:
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Applied {applied} manual mappings for {platform}",
                )

    def _fuzzy_match_parallel(
        self,
        unlinked_items: List[Dict],
        records: List[AnimeRecord],
        threshold: int = 85,
        title_preprocessor=None,
    ) -> List[Tuple[Dict, AnimeRecord]]:
        """Parallelized fuzzy matching using multiprocessing."""
        # Convert records to minimal dicts for multiprocessing (only title needed)
        record_dicts = [{"title": r.title} for r in records]

        # Prepare arguments
        args_list = [
            (item, record_dicts, threshold, title_preprocessor)
            for item in unlinked_items
        ]

        # Use multiprocessing
        num_processes = cpu_count()
        matches = []

        with Pool(processes=num_processes) as pool:
            results = pool.map(self._fuzzy_match_single, args_list)

            # Convert back to record objects
            for result in results:
                if result:
                    item, record_dict = result
                    # Find the actual record object
                    for record in records:
                        if record.title == record_dict["title"]:
                            matches.append((item, record))
                            break

        return matches

    def _fuzzy_match_single(self, args: Tuple) -> Optional[Tuple[Dict, Dict]]:
        """Match a single item against records using fuzzy matching."""
        item, record_dicts, threshold, title_preprocessor = args

        title = item.get("title", "")
        if title_preprocessor:
            title = title_preprocessor(title)

        best_match = None
        best_ratio = threshold - 1

        for record_dict in record_dicts:
            record_title = record_dict["title"]

            # Quick exact match
            if title == record_title:
                return (item, record_dict)

            # Fuzzy match
            ratio = fuzz.ratio(title, record_title)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = record_dict

                # Early termination for high scores
                if ratio >= 95:
                    break

        if best_match and best_ratio >= threshold:
            return (item, best_match)
        return None

    def _otakotaku_title_preprocessor(self, title: str) -> str:
        """Preprocess Otak Otaku titles for better matching."""
        replacements = {
            "Season 2": "2nd Season",
            "Season 3": "3rd Season",
        }

        # Generate ordinal replacements
        for i in range(4, 21):
            if i in [11, 12, 13]:
                replacements[f"Season {i}"] = f"{i}th Season"
            elif i % 10 == 1:
                replacements[f"Season {i}"] = f"{i}st Season"
            elif i % 10 == 2:
                replacements[f"Season {i}"] = f"{i}nd Season"
            elif i % 10 == 3:
                replacements[f"Season {i}"] = f"{i}rd Season"
            else:
                replacements[f"Season {i}"] = f"{i}th Season"

        for old, new in replacements.items():
            title = title.replace(old, new)

        return title

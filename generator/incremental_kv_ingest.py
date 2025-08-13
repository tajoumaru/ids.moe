# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Incremental KV Store ingestion module - uses Cloudflare Workers KV
"""

import json
from typing import Dict, List, Union
from dataclasses import asdict

from generator.const import (
    pprint,
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_KV_NAMESPACE_ID,
    CLOUDFLARE_AUTH_TOKEN,
)
from generator.prettyprint import Platform, Status
from generator.models import ChangeLog
from generator.anime_record import AnimeRecord


class IncrementalKVIngest:
    """Handles incremental ingestion of anime data into Cloudflare Workers KV"""

    def __init__(self) -> None:
        """Initialize Cloudflare Workers KV connection"""
        # Get Cloudflare KV credentials from const.py
        if not (CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_KV_NAMESPACE_ID and CLOUDFLARE_AUTH_TOKEN):
            pprint.print(
                Platform.SYSTEM,
                Status.ERR,
                "CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_KV_NAMESPACE_ID, and CLOUDFLARE_AUTH_TOKEN must be set",
            )
            raise ValueError("Missing Cloudflare KV credentials")
        
        # Initialize Cloudflare Workers KV client
        try:
            from generator.cloudflare_kv import CloudflareKV
            
            self.client = CloudflareKV(
                account_id=CLOUDFLARE_ACCOUNT_ID,
                namespace_id=CLOUDFLARE_KV_NAMESPACE_ID,
                auth_token=CLOUDFLARE_AUTH_TOKEN
            )
            pprint.print(
                Platform.SYSTEM, Status.INFO, "Using Cloudflare Workers KV connection"
            )
        except ImportError:
            pprint.print(
                Platform.SYSTEM, Status.ERR, "cloudflare_kv module not found"
            )
            raise

        # Test connection
        try:
            # Cloudflare KV doesn't have ping, so test with a simple get
            self.client.get("test_connection")
            pprint.print(Platform.SYSTEM, Status.PASS, "Connected to Cloudflare Workers KV")
        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.ERR, f"Failed to connect to Cloudflare Workers KV: {e}"
            )
            raise

    def _generate_platform_keys(
        self, record: AnimeRecord, internal_id: int
    ) -> List[str]:
        """
        Generate all platform-specific keys for a single anime record

        :param record: AnimeRecord instance
        :param internal_id: Internal unsigned integer ID
        :return: List of platform keys to map to internal_id
        """
        keys: List[str] = []

        # Simple platform IDs
        simple_platforms = [
            "anidb",
            "anilist",
            "animenewsnetwork",
            "animeplanet",
            "anisearch",
            "annict",
            "imdb",
            "kitsu",
            "livechart",
            "myanimelist",
            "notify",
            "otakotaku",
            "shikimori",
            "shoboi",
            "silveryasha",
            "simkl",
        ]

        for platform in simple_platforms:
            value = getattr(record, platform, None)
            if value is not None:
                keys.append(f"{platform}/{value}")

        # Special platforms with complex key patterns

        # Kaize - has both slug and ID
        if record.kaize is not None:
            keys.append(f"kaize/{record.kaize}")
        if record.kaize_id is not None:
            keys.append(f"kaize_id/{record.kaize_id}")

        # Nautiljon - has both slug and ID
        if record.nautiljon is not None:
            keys.append(f"nautiljon/{record.nautiljon}")
        if record.nautiljon_id is not None:
            keys.append(f"nautiljon_id/{record.nautiljon_id}")

        # Trakt - complex patterns based on type and season
        if record.trakt is not None and record.trakt_type is not None:
            if record.trakt_type in ["movie", "movies"]:
                keys.append(f"trakt/{record.trakt_type}/{record.trakt}")
            else:  # shows/tv
                # Base show key
                keys.append(f"trakt/{record.trakt_type}/{record.trakt}")
                # Season-specific key if season exists
                if record.trakt_season is not None:
                    keys.append(
                        f"trakt/{record.trakt_type}/{record.trakt}/seasons/{record.trakt_season}"
                    )

        # TheMovieDB - always movie format
        if record.themoviedb is not None:
            keys.append(f"themoviedb/movie/{record.themoviedb}")

        return keys

    def process_changes(self, changes: List[ChangeLog], db_ops) -> None:
        """
        Process incremental changes and update KV store

        :param changes: List of ChangeLog entries to process
        :param db_ops: Database operations instance to fetch anime data
        """
        if not changes:
            pprint.print(Platform.SYSTEM, Status.INFO, "No changes to process")
            return

        pprint.print(
            Platform.SYSTEM,
            Status.INFO,
            f"Processing {len(changes)} incremental changes to KV store",
        )

        # Group changes by type for bulk processing
        insert_updates = [c for c in changes if c.change_type in ("insert", "update")]
        deletes = [c for c in changes if c.change_type == "delete"]

        batch_data: Dict[str, Union[str, None]] = {}

        # Cloudflare KV supports up to 10000 operations per batch
        batch_size = 10000

        # Process deletes (simple - just mark anime IDs as deleted)
        for change in deletes:
            batch_data[str(change.anime_id)] = None

        # Process inserts/updates in bulk
        if insert_updates:
            anime_data_bulk = self._get_anime_data_bulk(
                db_ops, [c.anime_id for c in insert_updates]
            )

            for change in insert_updates:
                anime_id = change.anime_id
                anime_data = anime_data_bulk.get(anime_id)

                if anime_data:
                    # Generate platform keys
                    platform_keys = self._generate_platform_keys(anime_data, anime_id)

                    # Add platform key mappings
                    for key in platform_keys:
                        batch_data[key] = str(anime_id)

                    # Add the complete data
                    batch_data[str(anime_id)] = json.dumps(asdict(anime_data))

        # Execute in large batches
        processed_count = 0
        batch_count = 0
        total_keys = len(batch_data)
        total_batches = (total_keys + batch_size - 1) // batch_size

        if total_keys == 0:
            pprint.print(Platform.SYSTEM, Status.INFO, "No KV operations to execute")
            return

        pprint.print(
            Platform.SYSTEM,
            Status.INFO,
            f"Executing {total_keys} KV operations in {total_batches} batches",
        )

        batch_items = list(batch_data.items())
        for i in range(0, total_keys, batch_size):
            batch_count += 1
            batch_slice = dict(batch_items[i : i + batch_size])

            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Processing KV batch {batch_count}/{total_batches} ({len(batch_slice)} operations)",
            )
            self._execute_batch(batch_slice)
            processed_count += len(batch_slice)

        pprint.print(
            Platform.SYSTEM,
            Status.PASS,
            f"Processed {len(changes)} changes to KV store ({processed_count} operations)",
        )

    def _get_anime_data_bulk(
        self, db_ops, anime_ids: List[int]
    ) -> Dict[int, AnimeRecord]:
        """Get anime data from database by IDs in bulk - much faster than individual queries"""
        result_dict = {}

        if not anime_ids:
            return result_dict

        try:
            with db_ops.Session() as session:
                from sqlalchemy import select
                from generator.models import Anime

                # Single query to get all anime records
                results = (
                    session.execute(select(Anime).where(Anime.id.in_(anime_ids)))
                    .scalars()
                    .all()
                )

                for result in results:
                    # Convert ORM object to AnimeRecord
                    anime_record = AnimeRecord(
                        title=result.title,
                        myanimelist=result.myanimelist,
                        anilist=result.anilist,
                        anidb=result.anidb,
                        kitsu=result.kitsu,
                        animenewsnetwork=result.animenewsnetwork,
                        animeplanet=result.animeplanet,
                        anisearch=result.anisearch,
                        livechart=result.livechart,
                        notify=result.notify,
                        simkl=result.simkl,
                        shikimori=result.shikimori,
                        kaize=result.kaize,
                        kaize_id=result.kaize_id,
                        nautiljon=result.nautiljon,
                        nautiljon_id=result.nautiljon_id,
                        otakotaku=result.otakotaku,
                        silveryasha=result.silveryasha,
                        shoboi=result.shoboi,
                        annict=result.annict,
                        trakt=result.trakt,
                        trakt_type=result.trakt_type,
                        trakt_season=result.trakt_season,
                        imdb=result.imdb,
                        themoviedb=result.themoviedb,
                        data_hash=result.data_hash,
                    )
                    result_dict[result.id] = anime_record

                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Bulk fetched {len(result_dict)} anime records",
                )
                return result_dict

        except Exception as e:
            pprint.print(
                Platform.SYSTEM,
                Status.ERR,
                f"Error bulk fetching anime data: {e}",
            )
            return {}

    def _execute_batch(self, batch_data: Dict[str, Union[str, None]]) -> None:
        """Execute a batch of Cloudflare KV operations"""
        if not batch_data:
            return

        try:
            # Cloudflare KV - separate deletes and sets
            deletes = [k for k, v in batch_data.items() if v is None]
            sets = {k: v for k, v in batch_data.items() if v is not None}

            if deletes:
                self.client.delete(*deletes)
            if sets:
                self.client.mset(sets)

        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Failed to execute batch: {e}")
            # Try individual operations as fallback
            for key, value in batch_data.items():
                try:
                    if value is None:
                        self.client.delete(key)
                    else:
                        self.client.set(key, value)
                except Exception:
                    pass


    def prune_all_keys(self) -> None:
        """Delete all keys from Cloudflare Workers KV."""
        try:
            self.client.flushdb()
            pprint.print(Platform.SYSTEM, Status.INFO, "All Cloudflare KV keys deleted")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error pruning Cloudflare KV: {e}")
            raise


def process_incremental_changes(changes: List[ChangeLog], db_ops) -> None:
    """
    Public function to process incremental changes to KV store

    :param changes: List of ChangeLog entries to process
    :param db_ops: Database operations instance
    """
    ingester = IncrementalKVIngest()
    ingester.process_changes(changes, db_ops)

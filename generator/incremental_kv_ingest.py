"""
Incremental KV Store ingestion module - supports both regular Redis and Upstash Redis
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict

from generator.const import pprint
from generator.prettyprint import Platform, Status
from generator.models import ChangeLog
from generator.anime_record import AnimeRecord


class IncrementalKVIngest:
    """Handles incremental ingestion of anime data into dual KV store structure"""

    def __init__(self) -> None:
        """Initialize Redis connection - supports both regular Redis and Upstash"""
        self.client = None
        self.is_upstash = False

        # Check for Upstash credentials first
        upstash_url = os.getenv("KV_REST_API_URL")
        upstash_token = os.getenv("KV_REST_API_TOKEN")

        if upstash_url and upstash_token:
            # Use Upstash Redis client
            try:
                from upstash_redis import Redis as UpstashRedis

                self.client = UpstashRedis(url=upstash_url, token=upstash_token)
                self.is_upstash = True
                pprint.print(
                    Platform.SYSTEM, Status.INFO, "Using Upstash Redis connection"
                )
            except ImportError:
                pprint.print(
                    Platform.SYSTEM, Status.ERR, "upstash-redis package not installed"
                )
                raise
        else:
            # Fall back to regular Redis
            redis_url = os.getenv("REDIS_URL")
            redis_db = int(os.getenv("REDIS_DB", "0"))

            if not redis_url:
                pprint.print(
                    Platform.SYSTEM,
                    Status.ERR,
                    "Either KV_REST_API_URL/KV_REST_API_TOKEN or REDIS_URL must be set",
                )
                raise ValueError("Missing Redis credentials")

            try:
                import redis

                self.client = redis.from_url(redis_url, db=redis_db)
                self.is_upstash = False
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Using regular Redis connection (DB {redis_db})",
                )
            except ImportError:
                pprint.print(Platform.SYSTEM, Status.ERR, "redis package not installed")
                raise

        # Test connection
        try:
            if self.is_upstash:
                # Upstash doesn't have ping, so test with a simple get
                self.client.get("test_connection")
            else:
                # Regular Redis has ping
                self.client.ping()
            pprint.print(Platform.SYSTEM, Status.PASS, "Connected to KV store")
        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.ERR, f"Failed to connect to KV store: {e}"
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

        batch_data: Dict[str, Union[str, None]] = {}
        batch_size = (
            1000 if self.is_upstash else 100
        )  # Upstash can handle larger batches

        for change in changes:
            anime_id = change.anime_id
            change_type = change.change_type

            if change_type == "delete":
                # For deletions, we need to find and remove all keys that map to this internal ID
                # This is complex because we need to scan for keys - for now, we'll mark the internal ID as deleted
                batch_data[str(anime_id)] = None  # None means delete
            else:
                # For inserts/updates, get the current anime data
                anime_data = self._get_anime_data(db_ops, anime_id)
                if anime_data:
                    # Generate platform keys
                    platform_keys = self._generate_platform_keys(anime_data, anime_id)

                    # Add platform key mappings
                    for key in platform_keys:
                        batch_data[key] = str(anime_id)

                    # Add the complete data
                    batch_data[str(anime_id)] = json.dumps(asdict(anime_data))

            # Execute batch when it gets large enough
            if len(batch_data) >= batch_size:
                self._execute_batch(batch_data)
                batch_data = {}

        # Execute remaining batch
        if batch_data:
            self._execute_batch(batch_data)

        pprint.print(
            Platform.SYSTEM,
            Status.PASS,
            f"Processed {len(changes)} changes to KV store",
        )

    def _get_anime_data(self, db_ops, anime_id: int) -> Optional[AnimeRecord]:
        """Get anime data from database by ID"""
        try:
            with db_ops.Session() as session:
                from sqlalchemy import select
                from generator.models import Anime

                result = session.execute(
                    select(Anime).where(Anime.id == anime_id)
                ).scalar_one_or_none()

                if result:
                    # Convert ORM object to AnimeRecord
                    return AnimeRecord(
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
                return None
        except Exception as e:
            pprint.print(
                Platform.SYSTEM,
                Status.ERR,
                f"Error fetching anime data for ID {anime_id}: {e}",
            )
            return None

    def _execute_batch(self, batch_data: Dict[str, Union[str, None]]) -> None:
        """Execute a batch of KV operations"""
        if not batch_data:
            return

        try:
            if self.is_upstash:
                # Upstash Redis - separate deletes and sets
                deletes = [k for k, v in batch_data.items() if v is None]
                sets = {k: v for k, v in batch_data.items() if v is not None}

                if deletes:
                    self.client.delete(*deletes)
                if sets:
                    self.client.mset(sets)
            else:
                # Regular Redis - use pipeline for better performance
                pipeline = self.client.pipeline()
                for key, value in batch_data.items():
                    if value is None:
                        pipeline.delete(key)
                    else:
                        pipeline.set(key, value)
                pipeline.execute()

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

    def get_kv_stats(self) -> Dict[str, Any]:
        """Get KV store statistics"""
        try:
            if self.is_upstash:
                total_keys = self.client.dbsize()
            else:
                info = self.client.info()
                total_keys = info.get("db0", {}).get("keys", 0)

            return {
                "total_keys": total_keys,
                "connection_type": "upstash" if self.is_upstash else "redis",
            }
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error getting KV stats: {e}")
            return {"total_keys": 0, "connection_type": "unknown"}

    def prune_all_keys(self) -> None:
        """Delete all keys from the KV store."""
        try:
            if self.is_upstash:
                # Upstash Redis
                self.client.flushdb()
            else:
                # Regular Redis
                self.client.flushdb()

            pprint.print(Platform.SYSTEM, Status.INFO, "All KV store keys deleted")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error pruning KV store: {e}")
            raise


def process_incremental_changes(changes: List[ChangeLog], db_ops) -> None:
    """
    Public function to process incremental changes to KV store

    :param changes: List of ChangeLog entries to process
    :param db_ops: Database operations instance
    """
    ingester = IncrementalKVIngest()
    ingester.process_changes(changes, db_ops)

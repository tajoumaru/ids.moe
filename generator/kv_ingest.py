# SPDX-License-Identifier: AGPL-3.0-only

"""
KV Store ingestion module - converts final anime data to dual KV store format
"""

import os
import json
import redis
from typing import Any, Dict, List
from alive_progress import alive_bar  # type: ignore
from const import pprint
from prettyprint import Platform, Status


class KVIngest:
    """Handles ingestion of anime data into dual KV store structure"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.host = os.getenv("DRAGONFLY_HOST", "localhost")
        self.port = int(os.getenv("DRAGONFLY_PORT", "6379"))
        self.db = int(os.getenv("DRAGONFLY_DB", "0"))
        
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )
        
        # Test connection
        try:
            self.client.ping()
            pprint.print(Platform.SYSTEM, Status.PASS, f"Connected to KV store at {self.host}:{self.port}")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Failed to connect to KV store: {e}")
            raise
    
    def clear_all_data(self) -> None:
        """Clear all existing data from KV store"""
        try:
            self.client.flushdb()
            pprint.print(Platform.SYSTEM, Status.INFO, "Cleared all existing KV store data")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.ERR, f"Failed to clear KV store: {e}")
            raise
    
    def _generate_platform_keys(self, item: Dict[str, Any], internal_id: int) -> List[str]:
        """
        Generate all platform-specific keys for a single anime item
        
        :param item: Single anime data item
        :param internal_id: Internal unsigned integer ID
        :return: List of platform keys to map to internal_id
        """
        keys = []
        
        # Simple platform IDs
        simple_platforms = [
            "anidb", "anilist", "animenewsnetwork", "animeplanet", "anisearch", 
            "annict", "imdb", "kitsu", "livechart", "myanimelist", "notify", 
            "otakotaku", "shikimori", "shoboi", "silveryasha", "simkl"
        ]
        
        for platform in simple_platforms:
            value = item.get(platform)
            if value is not None:
                keys.append(f"{platform}/{value}")
        
        # Special platforms with complex key patterns
        
        # Kaize - has both slug and ID
        kaize_slug = item.get("kaize")
        kaize_id = item.get("kaize_id")
        if kaize_slug is not None:
            keys.append(f"kaize/{kaize_slug}")
        if kaize_id is not None:
            keys.append(f"kaize_id/{kaize_id}")
        
        # Nautiljon - has both slug and ID  
        nautiljon_slug = item.get("nautiljon")
        nautiljon_id = item.get("nautiljon_id")
        if nautiljon_slug is not None:
            keys.append(f"nautiljon/{nautiljon_slug}")
        if nautiljon_id is not None:
            keys.append(f"nautiljon_id/{nautiljon_id}")
        
        # Trakt - complex patterns based on type and season
        trakt_id = item.get("trakt")
        trakt_type = item.get("trakt_type")
        trakt_season = item.get("trakt_season")
        
        if trakt_id is not None and trakt_type is not None:
            if trakt_type in ["movie", "movies"]:
                keys.append(f"trakt/{trakt_type}/{trakt_id}")
            else:  # shows/tv
                # Base show key
                keys.append(f"trakt/{trakt_type}/{trakt_id}")
                # Season-specific key if season exists
                if trakt_season is not None:
                    keys.append(f"trakt/{trakt_type}/{trakt_id}/seasons/{trakt_season}")
        
        # TheMovieDB - always movie format
        themoviedb_id = item.get("themoviedb")
        if themoviedb_id is not None:
            keys.append(f"themoviedb/movie/{themoviedb_id}")
        
        return keys
    
    def ingest_data(self, final_data: List[Dict[str, Any]]) -> None:
        """
        Ingest final anime data into dual KV store structure using pipelining for performance
        
        :param final_data: List of anime data items from main.py
        """
        pprint.print(Platform.SYSTEM, Status.INFO, f"Starting KV ingestion for {len(final_data)} anime entries")
        
        # Clear existing data
        self.clear_all_data()
        
        internal_id_counter = 1
        batch_size = 1000  # Process in batches for better memory management
        total_keys_generated = 0
        seen_keys = set()  # Track duplicate keys
        duplicate_count = 0
        
        with alive_bar(len(final_data), title="Ingesting data to KV store", spinner=None) as bar:  # type: ignore
            pipe = self.client.pipeline()
            commands_in_batch = 0
            
            for item in final_data:
                # Skip items that have no platform IDs at all
                has_any_id = any(
                    item.get(platform) is not None 
                    for platform in ["anidb", "anilist", "animenewsnetwork", "animeplanet", 
                                   "anisearch", "annict", "imdb", "kaize", "kaize_id", 
                                   "kitsu", "livechart", "myanimelist", "nautiljon", 
                                   "nautiljon_id", "notify", "otakotaku", "shikimori", 
                                   "shoboi", "silveryasha", "simkl", "themoviedb", "trakt"]
                )
                
                if not has_any_id:
                    bar()
                    continue
                
                # Generate all platform keys for this item
                platform_keys = self._generate_platform_keys(item, internal_id_counter)
                total_keys_generated += len(platform_keys)
                
                # Store 1: external_id -> internal_id mappings (batched)
                for key in platform_keys:
                    if key in seen_keys:
                        duplicate_count += 1
                    else:
                        seen_keys.add(key)
                    pipe.set(key, str(internal_id_counter))
                    commands_in_batch += 1
                
                # Store 2: internal_id -> complete data (batched)
                pipe.set(str(internal_id_counter), json.dumps(item))
                commands_in_batch += 1
                
                # Execute batch when it gets large enough
                if commands_in_batch >= batch_size:
                    try:
                        pipe.execute()
                        pipe = self.client.pipeline()  # Reset pipeline
                        commands_in_batch = 0
                    except Exception as e:
                        pprint.print(Platform.SYSTEM, Status.ERR, f"Failed to execute batch: {e}")
                        pipe = self.client.pipeline()  # Reset pipeline on error
                        commands_in_batch = 0
                
                internal_id_counter += 1
                bar()
            
            # Execute remaining commands in pipeline
            if commands_in_batch > 0:
                try:
                    pipe.execute()
                except Exception as e:
                    pprint.print(Platform.SYSTEM, Status.ERR, f"Failed to execute final batch: {e}")
        
        total_keys = self.client.dbsize()
        pprint.print(Platform.SYSTEM, Status.PASS, f"KV ingestion completed. Total keys stored: {total_keys}")
        pprint.print(Platform.SYSTEM, Status.INFO, f"Generated {total_keys_generated} platform keys + {internal_id_counter - 1} data keys = {total_keys_generated + internal_id_counter - 1} expected")
        if duplicate_count > 0:
            pprint.print(Platform.SYSTEM, Status.WARN, f"Found {duplicate_count} duplicate keys (these overwrite previous values)")
        pprint.print(Platform.SYSTEM, Status.INFO, f"Assigned internal IDs: 1 to {internal_id_counter - 1}")
        
        # Report any discrepancy
        expected_total = total_keys_generated + (internal_id_counter - 1)
        expected_unique = expected_total - duplicate_count
        if total_keys != expected_unique:
            pprint.print(Platform.SYSTEM, Status.ERR, f"KEY MISMATCH: Expected {expected_unique} unique keys, but stored {total_keys}. Missing {expected_unique - total_keys} keys!")


def ingest_to_kv_store(final_data: List[Dict[str, Any]]) -> None:
    """
    Public function to ingest anime data to KV store
    
    :param final_data: Final anime data from main.py
    """
    ingester = KVIngest()
    ingester.ingest_data(final_data)

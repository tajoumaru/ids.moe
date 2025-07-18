# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Anime record data structures.
"""

import hashlib
from typing import Optional
from dataclasses import dataclass


@dataclass
class AnimeRecord:
    """Represents a structured anime record for database storage."""

    title: str

    # Core platform IDs
    myanimelist: Optional[int] = None
    anilist: Optional[int] = None
    anidb: Optional[int] = None
    kitsu: Optional[int] = None

    # Additional platform IDs
    animenewsnetwork: Optional[int] = None
    animeplanet: Optional[int] = None
    anisearch: Optional[int] = None
    annict: Optional[int] = None
    imdb: Optional[str] = None
    livechart: Optional[int] = None
    notify: Optional[int] = None
    otakotaku: Optional[int] = None
    shikimori: Optional[int] = None
    shoboi: Optional[int] = None
    silveryasha: Optional[int] = None
    simkl: Optional[int] = None
    themoviedb: Optional[int] = None

    # Kaize (has both slug and ID)
    kaize: Optional[str] = None
    kaize_id: Optional[int] = None

    # Nautiljon (has both slug and ID)
    nautiljon: Optional[str] = None
    nautiljon_id: Optional[int] = None

    # Trakt (complex structure)
    trakt: Optional[int] = None
    trakt_type: Optional[str] = None
    trakt_season: Optional[int] = None

    # Internal tracking
    data_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute SHA256 hash of record data for change detection."""
        # Create a consistent string representation of the record
        data_str = (
            f"{self.title}|{self.myanimelist}|{self.anilist}|{self.anidb}|{self.kitsu}|"
        )
        data_str += f"{self.animenewsnetwork}|{self.animeplanet}|{self.anisearch}|{self.annict}|"
        data_str += f"{self.imdb}|{self.livechart}|{self.notify}|{self.otakotaku}|{self.shikimori}|"
        data_str += f"{self.shoboi}|{self.silveryasha}|{self.simkl}|{self.themoviedb}|"
        data_str += (
            f"{self.kaize}|{self.kaize_id}|{self.nautiljon}|{self.nautiljon_id}|"
        )
        data_str += f"{self.trakt}|{self.trakt_type}|{self.trakt_season}"

        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

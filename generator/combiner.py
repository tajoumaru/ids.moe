# SPDX-License-Identifier: AGPL-3.0-only AND MIT

from typing import Any

from alive_progress import alive_bar  # type: ignore
from const import pprint
from prettyprint import Platform, Status


def combine_arm(
    arm: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Combine ARM data with AOD data

    :param arm: ARM data
    :type arm: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: AOD data
    :rtype: list[dict[str, Any]]
    """
    # Pre-index ARM data by MAL ID and AniList ID for O(1) lookups
    pprint.print(Platform.ARM, Status.INFO, "Indexing ARM data for fast lookups")
    arm_by_mal = {}
    arm_by_anilist = {}
    
    for arm_item in arm:
        mal_id = arm_item.get("mal_id", None)
        anilist_id = arm_item.get("anilist_id", None)
        
        if mal_id is not None:
            arm_by_mal[mal_id] = arm_item
        if anilist_id is not None:
            arm_by_anilist[anilist_id] = arm_item
    
    linked = 0
    with alive_bar(
        len(aod), title="Combining ARM data with AOD data", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            myanimelist = item["myanimelist"]
            anilist = item["anilist"]
            
            # Skip if both myanimelist and anilist are null
            if myanimelist is None and anilist is None:
                item.update({
                    "shoboi": None,
                    "annict": None,
                })
                bar()
                continue

            # O(1) lookup instead of O(n) search
            arm_item = None
            if myanimelist is not None and myanimelist in arm_by_mal:
                arm_item = arm_by_mal[myanimelist]
                syoboi = arm_item.get("syobocal_tid", None)
                annict = arm_item.get("annict_id", None)
                anilist_id = arm_item.get("anilist_id", None)
                
                item.update({
                    "shoboi": syoboi,
                    "annict": annict,
                    "anilist": anilist if anilist is not None else anilist_id,
                })
                linked += 1
            elif anilist is not None and anilist in arm_by_anilist:
                arm_item = arm_by_anilist[anilist]
                syoboi = arm_item.get("syobocal_tid", None)
                annict = arm_item.get("annict_id", None)
                mal_id = arm_item.get("mal_id", None)
                
                item.update({
                    "shoboi": syoboi,
                    "annict": annict,
                    "myanimelist": myanimelist if myanimelist is not None else mal_id,
                    "shikimori": myanimelist if myanimelist is not None else mal_id,
                })
                linked += 1
            else:
                # No match found
                item.update({
                    "shoboi": None,
                    "annict": None,
                })
            bar()
    pprint.print(
        Platform.ARM,
        Status.PASS,
        "ARM data combined with AOD data.",
        "Total linked data:",
        f"{linked},",
        "AOD data:",
        f"{len(aod)}",
        "ARM data:",
        f"{len(arm)}",
    )
    return aod


def combine_anitrakt(
    anitrakt: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Combine AniTrakt data with AOD data

    :param anitrakt: AniTrakt data
    :type anitrakt: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: AOD data
    :rtype: list[dict[str, Any]]
    """
    # Pre-index AniTrakt data by MAL ID for O(1) lookups
    pprint.print(Platform.ANITRAKT, Status.INFO, "Indexing AniTrakt data for fast lookups")
    anitrakt_by_mal = {}
    
    for anitrakt_item in anitrakt:
        mal_id = anitrakt_item.get("mal_id", None)
        if mal_id is not None:
            anitrakt_by_mal[mal_id] = anitrakt_item
    
    linked = 0
    with alive_bar(
        len(aod), title="Combining AniTrakt data with AOD data", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            myanimelist = item["myanimelist"]
            
            # Skip if myanimelist is null
            if myanimelist is None:
                item.update({
                    "trakt": None,
                    "trakt_type": None,
                    "trakt_season": None,
                })
                bar()
                continue

            # O(1) lookup instead of O(n) search
            if myanimelist in anitrakt_by_mal:
                anitrakt_item = anitrakt_by_mal[myanimelist]
                trakt = anitrakt_item.get("trakt_id", None)
                media_type = anitrakt_item.get("type", None)
                media_season = anitrakt_item.get("season", None)
                
                item.update({
                    "trakt": trakt,
                    "trakt_type": media_type,
                    "trakt_season": media_season,
                })
                linked += 1
            else:
                # No match found
                item.update({
                    "trakt": None,
                    "trakt_type": None,
                    "trakt_season": None,
                })
            bar()
    pprint.print(
        Platform.ANITRAKT,
        Status.PASS,
        "AniTrakt data combined with AOD data.",
        "Total linked data:",
        f"{linked},",
        "AOD data:",
        f"{len(aod)}",
        "AniTrakt data:",
        f"{len(anitrakt)}",
    )
    return aod


def combine_fribb(
    fribb: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Combine Fribb's Animelists data with AOD data to obtain IMDb and TMDB IDs
    via AniDB

    :param fribb: Fribb's Animelists data
    :type fribb: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: AOD data
    :rtype: list[dict[str, Any]]
    """
    # Pre-index Fribb data by AniDB ID for O(1) lookups
    pprint.print(Platform.FRIBB, Status.INFO, "Indexing Fribb data for fast lookups")
    fribb_by_anidb = {}
    
    for fbi in fribb:
        anidb_id = fbi.get("anidb_id", None)
        if anidb_id is not None:
            fribb_by_anidb[anidb_id] = fbi
    
    linked = 0
    with alive_bar(
        len(aod), title="Combining Fribb's Animelists data with AOD data", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            anidb = item["anidb"]
            
            # Skip if anidb is null
            if anidb is None:
                item.update({
                    "imdb": None,
                    "themoviedb": None,
                })
                bar()
                continue

            # O(1) lookup instead of O(n) search
            if anidb in fribb_by_anidb:
                fbi = fribb_by_anidb[anidb]
                imdb = fbi.get("imdb_id", None)
                tmdb: str | int | None = fbi.get("themoviedb_id", None)
                
                # Process TMDB ID (handle comma-separated values)
                if isinstance(tmdb, str):
                    tmdbl = tmdb.split(",")
                    tmdb = int(tmdbl[0])
                
                item.update({
                    "imdb": imdb,
                    "themoviedb": tmdb,
                })
                linked += 1
            else:
                # No match found
                item.update({
                    "imdb": None,
                    "themoviedb": None,
                })
            bar()
    pprint.print(
        Platform.FRIBB,
        Status.PASS,
        "Fribb's Animelists data combined with AOD data.",
        "Total linked data:",
        f"{linked},",
        "AOD data:",
        f"{len(aod)}",
        "Fribb's Animelists data:",
        f"{len(fribb)}",
    )
    return aod

# SPDX-License-Identifier: AGPL-3.0-only AND MIT

import json
from typing import Any, Union
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

from alive_progress import alive_bar  # type: ignore
from const import pprint
from fuzzywuzzy import fuzz  # type: ignore
from prettyprint import Platform, Status
from slugify import slugify


def _otakotaku_title_preprocessor(title):
    """
    OtakOtaku-specific title preprocessing function
    """
    replace_dict = {
        "Season 2": "2nd Season",
        "Season 3": "3rd Season",
    }
    # autopopulate the replace dict with ordinal numbers from 4 to 100
    for i in range(4, 21):
        # if it's 11, 12, 13, use th, else use st, nd, rd
        if i in [11, 12, 13]:
            replace_dict[f"Season {i}"] = f"{i}th Season"
        elif i % 10 == 1:
            replace_dict[f"Season {i}"] = f"{i}st Season"
        elif i % 10 == 2:
            replace_dict[f"Season {i}"] = f"{i}nd Season"
        elif i % 10 == 3:
            replace_dict[f"Season {i}"] = f"{i}rd Season"
        else:
            replace_dict[f"Season {i}"] = f"{i}th Season"
    
    for key, value in replace_dict.items():
        title = title.replace(key, value)
    return title


def _fuzzy_match_single_item(args):
    """
    Match a single item against AOD items - designed for multiprocessing
    
    :param args: Tuple of (item, aod_items, threshold, title_preprocessor)
    :return: (item, best_match) or None if no match
    """
    try:
        item, aod_items, threshold, title_preprocessor = args
        
        title = item["title"]
        if title_preprocessor:
            title = title_preprocessor(title)
        
        best_match = None
        best_ratio = threshold - 1
        
        # Early termination at perfect match
        for aod_item in aod_items:
            aod_title = aod_item["title"]
            
            # Quick exact match check first
            if title == aod_title:
                return (item, aod_item)
            
            # Fuzzy matching
            ratio = fuzz.ratio(title, aod_title)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = aod_item
                
                # If we hit a very high score, accept it immediately
                if ratio >= 95:
                    break
        
        if best_match and best_ratio >= threshold:
            return (item, best_match)
        return None
    except Exception as e:
        # Return the error with the item for debugging
        return ("ERROR", str(e), item.get("title", "unknown"))


def _fuzzy_match_optimized(unlinked_items: list[dict[str, Any]], aod_items: list[dict[str, Any]], threshold: int = 85, title_preprocessor=None):
    """
    Parallelized fuzzy matching that uses all CPU cores via multiprocessing
    
    :param unlinked_items: Items to match
    :param aod_items: AOD items to match against  
    :param threshold: Minimum fuzzy ratio
    :param title_preprocessor: Optional function to preprocess titles
    :return: List of (unlinked_item, matched_aod_item) tuples
    """
    # Pre-sort AOD items by title length for potential early wins
    aod_sorted = sorted(aod_items, key=lambda x: len(x.get("title", "")))
    
    # Prepare arguments for multiprocessing
    args_list = [(item, aod_sorted, threshold, title_preprocessor) for item in unlinked_items]
    
    # Use all available CPU cores
    num_processes = cpu_count()
    pprint.print(Platform.SYSTEM, Status.INFO, f"Using {num_processes} CPU cores for fuzzy matching")
    
    matches = []
    errors = []
    with Pool(processes=num_processes) as pool:
        results = pool.map(_fuzzy_match_single_item, args_list)
        
        # Filter results and collect errors
        for result in results:
            if result is None:
                continue
            elif isinstance(result, tuple) and len(result) == 3 and result[0] == "ERROR":
                errors.append(result)
            else:
                matches.append(result)
    
    # Report any errors found
    if errors:
        pprint.print(Platform.SYSTEM, Status.ERR, f"Fuzzy matching errors: {len(errors)} items failed")
        for error_type, error_msg, title in errors[:5]:  # Show first 5 errors
            pprint.print(Platform.SYSTEM, Status.ERR, f"Error matching '{title}': {error_msg}")
        if len(errors) > 5:
            pprint.print(Platform.SYSTEM, Status.ERR, f"... and {len(errors) - 5} more errors")
    
    return matches


def link_kaize_to_mal(
    kaize: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Link Kaize slug to MyAnimeList ID based similarity in title name over 85% in
    fuzzy search

    :param kaize: Kaize data
    :type kaize: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: Crude AniAPI data, requires refinement after the process
    :rtype: list[dict[str, Any]]
    """
    # add dummy data to aod
    with alive_bar(
        len(aod), title="Adding dummy Kaize data to AOD", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            item.update(
                {
                    "kaize": None,
                    "kaize_id": None,
                }
            )
            bar()
    unlinked: list[dict[str, Any]] = []
    kz_fixed: list[dict[str, Any]] = []
    kz_dict: dict[str, Any] = {}
    aod_dict: dict[str, Any] = {}
    with alive_bar(
        len(aod), title="Translating AOD list to a dict with custom slug", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            aod_slug = slugify(item["title"]).replace("-", "")
            aod_dict[aod_slug] = item
            bar()
    with alive_bar(
        len(kaize),
        title="Translating Kaize list to a dict with custom slug",
        spinner=None,
    ) as bar:  # type: ignore
        for item in kaize:
            kz_slug = slugify(item["slug"]).replace("-", "")
            kz_dict[kz_slug] = item
            bar()
    with alive_bar(
        len(kz_dict), title="Linking Kaize slug to MyAnimeList ID", spinner=None
    ) as bar:  # type: ignore
        for kz_slug, kz_item in kz_dict.items():
            if kz_slug in aod_dict:
                aod_item: Union[dict[str, Any], None] = aod_dict.get(kz_slug, None)
                if aod_item:
                    # add more data from kaize
                    kz_item.update(
                        {
                            "anidb": aod_item["anidb"],
                            "anilist": aod_item["anilist"],
                            "myanimelist": aod_item["myanimelist"],
                        }
                    )
                    kz_fixed.append(kz_item)
                    aod_item.update(
                        {
                            "kaize": kz_item["slug"],
                            "kaize_id": None
                            if kz_item["kaize"] == 0
                            else kz_item["kaize"],
                        }
                    )
                else:
                    unlinked.append(kz_item)
            else:
                unlinked.append(kz_item)
            bar()
    # on unlinked, fuzzy search the title name (optimized)
    pprint.print(Platform.KAIZE, Status.INFO, f"Optimized fuzzy matching {len(unlinked)} items")
    matches = _fuzzy_match_optimized(unlinked, aod, threshold=85)
    
    with alive_bar(
        len(matches), title="Processing fuzzy matches", spinner=None, disable=True
    ) as bar:  # type: ignore
        for item, aod_item in matches:
            kz_dat = {
                "anidb": aod_item["anidb"],
                "anilist": aod_item["anilist"],
                "myanimelist": aod_item["myanimelist"],
            }
            item.update(kz_dat)
            kz_fixed.append(item)
            aod_item.update(
                {
                    "kaize": item["slug"],
                    "kaize_id": None if item["kaize"] == 0 else item["kaize"],
                }
            )
            bar()
    # load manual link data
    with open("database/raw/kaize_manual.json", "r", encoding="utf-8") as file:
        manual_link: dict[str, dict[str, str | int | None]] = json.load(file)
    
    # Pre-index AOD by title for O(1) lookups
    aod_by_title = {item["title"]: item for item in aod}
    
    with alive_bar(
        len(manual_link), title="Insert manual mappings", spinner=None
    ) as bar:  # type: ignore
        for title, kz_item in manual_link.items():
            if isinstance(kz_item, list):
                kz_item = kz_item[0]
                override = True
            else:
                override = False
            # if kz_item["kaize"] doesn't exist in unlinked under slug key, skip
            if override is False and kz_item["kaize"] not in [
                item["slug"] for item in unlinked
            ]:
                bar()
                continue
            
            # O(1) lookup instead of O(n) search
            aod_item = aod_by_title.get(title)
            if aod_item:
                kz_dat = {
                    "kaize": kz_item["kaize"],
                    "kaize_id": None
                    if kz_item["kaize_id"] == 0
                    else kz_item["kaize_id"],
                }
                aod_item.update(kz_dat)
                kz_fixed.append(aod_item)
                # in unlinked, remove the item with the same id (optimized)
                unlinked = [item for item in unlinked if item["kaize"] != kz_item["kaize"]]
            bar()
    # remove if unlinked data is already linked (optimized with set)
    fixed_ids = {item["kaize"] for item in kz_fixed if "kaize" in item}
    original_count = len(unlinked)
    with alive_bar(
        original_count, title="Removing unrequired data from unlinked", spinner=None
    ) as bar:  # type: ignore
        unlinked = [item for item in unlinked if item["kaize"] not in fixed_ids]
        for _ in range(original_count):
            bar()
    aod_list: list[dict[str, Any]] = []
    with alive_bar(
        len(aod_dict), title="Translating AOD dict to a list", spinner=None
    ) as bar:  # type: ignore
        for _, value in aod_dict.items():
            # check if kaize_id or kaize key not exists, then set it to None
            if "kaize" not in value:
                value["kaize"] = None
            if "kaize_id" not in value:
                value["kaize_id"] = None
            aod_list.append(value)
            bar()
    
    # Use set of IDs for O(1) membership testing instead of O(n) object comparison
    aod_ids = set()
    with alive_bar(
        len(aod), title="Building AOD ID index for deduplication", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            # Create unique identifier from available IDs
            if item.get("myanimelist"):
                aod_ids.add(("mal", item["myanimelist"]))
            elif item.get("anilist"):
                aod_ids.add(("anilist", item["anilist"]))
            elif item.get("title"):
                aod_ids.add(("title", item["title"]))
            bar()
    
    merged: list[dict[str, Any]] = []
    merged.extend(aod)

    # add missing items from old AOD data
    with alive_bar(
        len(aod_list), title="Reintroduce old list items", spinner=None
    ) as bar:  # type: ignore
        for item in aod_list:
            # Check if this item already exists using ID-based lookup
            item_id = None
            if item.get("myanimelist"):
                item_id = ("mal", item["myanimelist"])
            elif item.get("anilist"):
                item_id = ("anilist", item["anilist"])
            elif item.get("title"):
                item_id = ("title", item["title"])
            
            if item_id and item_id not in aod_ids:
                merged.append(item)
                aod_ids.add(item_id)  # Add to set to avoid duplicates
            bar()

    aod_list = merged

    pprint.print(
        Platform.KAIZE,
        Status.PASS,
        "Kaize slug linked to MyAnimeList ID, unlinked data will be saved to kaize_unlinked.json.",
        "Total linked data:",
        f"{len(kz_fixed)},",
        "total unlinked data:",
        f"{len(unlinked)}",
    )
    with open("database/raw/kaize_unlinked.json", "w", encoding="utf-8") as file:
        json.dump(unlinked, file)
    return aod_list


def link_nautiljon_to_mal(
    nautiljon: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Link Nautiljon ID to MyAnimeList ID based similarity in title name over 85%
    in fuzzy search

    :param nautiljon: Nautiljon data
    :type nautiljon: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: Crude AniAPI data, requires refinement after the process
    :rtype: list[dict[str, Any]]
    """
    with alive_bar(
        len(aod), title="Adding dummy Nautiljon data to AOD", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            item.update(
                {
                    "nautiljon": None,
                    "nautiljon_id": None,
                }
            )
            bar()
    unlinked: list[dict[str, Any]] = []
    nautiljon_fixed: list[dict[str, Any]] = []
    nautiljon_dict: dict[str, Any] = {}
    aod_dict: dict[str, Any] = {}
    with alive_bar(
        len(aod),
        title="Translating AOD list to a dict using title as key",
        spinner=None,
    ) as bar:  # type: ignore
        for item in aod:
            # if previous key exists, skip
            if item["title"] in aod_dict:
                bar()
                continue
            aod_dict[item["title"]] = item
            bar()
    with alive_bar(
        len(nautiljon),
        title="Translating Nautiljon list to a dict with title as key",
        spinner=None,
    ) as bar:  # type: ignore
        for item in nautiljon:
            nautiljon_dict[item["title"]] = item
            bar()
    # link nautiljon to aod
    with alive_bar(
        len(nautiljon_dict), title="Linking Nautiljon ID to AOD", spinner=None
    ) as bar:  # type: ignore
        for title, nautiljon_item in nautiljon_dict.items():
            if title in aod_dict:
                aod_item = aod_dict.get(title)
                if aod_item:
                    aod_item.update(
                        {
                            "nautiljon": nautiljon_item["slug"],
                            "nautiljon_id": nautiljon_item["entry_id"],
                        }
                    )
                    nautiljon_item.update(
                        {
                            "anidb": aod_item["anidb"],
                            "anilist": aod_item["anilist"],
                            "myanimelist": aod_item["myanimelist"],
                        }
                    )
                    nautiljon_fixed.append(nautiljon_item)
                else:
                    unlinked.append(nautiljon_item)
            else:
                unlinked.append(nautiljon_item)
            bar()
    # fuzzy search the rest of unlinked data (optimized)
    pprint.print(Platform.NAUTILJON, Status.INFO, f"Optimized fuzzy matching {len(unlinked)} items")
    matches = _fuzzy_match_optimized(unlinked, aod, threshold=90)
    
    with alive_bar(
        len(matches), title="Processing fuzzy matches", spinner=None, disable=True
    ) as bar:  # type: ignore
        for item, aod_item in matches:
            item.update(
                {
                    "anidb": aod_item["anidb"],
                    "anilist": aod_item["anilist"],
                    "myanimelist": aod_item["myanimelist"],
                }
            )
            nautiljon_fixed.append(item)
            aod_item.update(
                {
                    "nautiljon": item["slug"],
                    "nautiljon_id": item["entry_id"],
                }
            )
            bar()
    # remove fixed data from unlinked (optimized with set)
    fixed_slugs = {item["slug"] for item in nautiljon_fixed}
    original_count = len(unlinked)
    with alive_bar(
        original_count, title="Removing fixed data from unlinked", spinner=None
    ) as bar:  # type: ignore
        unlinked = [item for item in unlinked if item["slug"] not in fixed_slugs]
        for _ in range(original_count):
            bar()
    aod_list: list[dict[str, Any]] = []
    with alive_bar(
        len(aod_dict), title="Translating AOD dict to a list", spinner=None
    ) as bar:  # type: ignore
        for _, value in aod_dict.items():
            aod_list.append(value)
            bar()
    # Use set of IDs for O(1) membership testing instead of O(n) object comparison
    aod_ids = set()
    with alive_bar(
        len(aod), title="Building AOD ID index for deduplication", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            # Create unique identifier from available IDs
            if item.get("myanimelist"):
                aod_ids.add(("mal", item["myanimelist"]))
            elif item.get("anilist"):
                aod_ids.add(("anilist", item["anilist"]))
            elif item.get("title"):
                aod_ids.add(("title", item["title"]))
            bar()
    
    merged: list[dict[str, Any]] = []
    merged.extend(aod_list)
    with alive_bar(
        len(aod_list), title="Reintroduce old list items", spinner=None
    ) as bar:  # type: ignore
        for item in aod_list:
            # Check if this item already exists using ID-based lookup
            item_id = None
            if item.get("myanimelist"):
                item_id = ("mal", item["myanimelist"])
            elif item.get("anilist"):
                item_id = ("anilist", item["anilist"])
            elif item.get("title"):
                item_id = ("title", item["title"])
            
            if item_id and item_id not in aod_ids:
                merged.append(item)
                aod_ids.add(item_id)  # Add to set to avoid duplicates
            bar()

    pprint.print(
        Platform.NAUTILJON,
        Status.PASS,
        "Nautiljon slug linked to MyAnimeList ID, unlinked data will be saved to nautiljon_unlinked.json.",
        "Total linked data:",
        f"{len(nautiljon_fixed)},",
        "total unlinked data:",
        f"{len(unlinked)}",
    )
    with open("database/raw/nautiljon_unlinked.json", "w", encoding="utf-8") as file:
        json.dump(unlinked, file)
    return merged


def link_otakotaku_to_mal(
    otakotaku: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Link Otak Otaku ID to MyAnimeList ID based similarity in title name over 85%
    in fuzzy search

    :param otakotaku: Otak Otaku data
    :type otakotaku: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: Crude AniAPI data, requires refinement after the process
    :rtype: list[dict[str, Any]]
    """
    unlinked: list[dict[str, Any]] = []
    ot_fixed: list[dict[str, Any]] = []
    ot_dict: dict[str, Any] = {}
    aod_dict: dict[str, Any] = {}
    with alive_bar(
        len(aod), title="Translating AOD list to a dict with MAL ID", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            aod_dict[item["title"]] = item
            bar()
    with alive_bar(
        len(otakotaku),
        title="Translating Otakotaku list to a dict with MAL ID",
        spinner=None,
    ) as bar:  # type: ignore
        for item in otakotaku:
            ot_dict[item["title"]] = item
            bar()
    with alive_bar(
        len(ot_dict), title="Linking Otak Otaku ID to MyAnimeList ID", spinner=None
    ) as bar:  # type: ignore
        for title, ot_item in ot_dict.items():
            if title in aod_dict:
                aod_item: Union[dict[str, Any], None] = aod_dict.get(title, None)
                if aod_item:
                    # add more data from otakotaku
                    ot_dat = {
                        "otakotaku": ot_item["otakotaku"],
                    }
                    aod_item.update(ot_dat)
                    ot_fixed.append(aod_item)
                else:
                    unlinked.append(ot_item)
            else:
                unlinked.append(ot_item)
            bar()
    # on unlinked, fuzzy search the title name (optimized)
    pprint.print(Platform.OTAKOTAKU, Status.INFO, f"Optimized fuzzy matching {len(unlinked)} items")
    matches = _fuzzy_match_optimized(unlinked, aod, threshold=90, title_preprocessor=_otakotaku_title_preprocessor)
    
    with alive_bar(
        len(matches), title="Processing fuzzy matches", spinner=None, disable=True
    ) as bar:  # type: ignore
        for item, aod_item in matches:
            ot_dat = {
                "otakotaku": item["otakotaku"],
            }
            aod_item.update(ot_dat)
            ot_fixed.append(aod_item)
            bar()
    # load manual link data
    with open("database/raw/otakotaku_manual.json", "r", encoding="utf-8") as file:
        manual_link: dict[str, int] = json.load(file)
    
    # Pre-index AOD by title for O(1) lookups
    aod_by_title = {item["title"]: item for item in aod}
    
    with alive_bar(
        len(manual_link), title="Insert manual mappings", spinner=None
    ) as bar:  # type: ignore
        for title, oo_id in manual_link.items():
            if isinstance(oo_id, list):
                oo_id = oo_id[0]
                override = True
            else:
                override = False
            # skip if not in unlinked
            if override is False and oo_id not in [
                item["otakotaku"] for item in unlinked
            ]:
                bar()
                continue
            
            # O(1) lookup instead of O(n) search
            aod_item = aod_by_title.get(title)
            if aod_item:
                oo_dat = {"otakotaku": oo_id}
                aod_item.update(oo_dat)
                ot_fixed.append(aod_item)
                # in unlinked, remove the item with the same id (optimized)
                unlinked = [item for item in unlinked if item["otakotaku"] != oo_id]
            bar()
    # remove if unlinked data is already linked (optimized with set)
    fixed_ids = {item["otakotaku"] for item in ot_fixed if "otakotaku" in item}
    original_count = len(unlinked)
    with alive_bar(
        original_count, title="Removing unrequired data from unlinked", spinner=None
    ) as bar:  # type: ignore
        unlinked = [item for item in unlinked if item["otakotaku"] not in fixed_ids]
        for _ in range(original_count):
            bar()
    aod_list: list[dict[str, Any]] = []
    with alive_bar(
        len(aod_dict), title="Translating AOD dict to a list", spinner=None
    ) as bar:  # type: ignore
        for _, value in aod_dict.items():
            if "otakotaku" not in value:
                value["otakotaku"] = None
            aod_list.append(value)
            bar()
    
    # Use set of IDs for O(1) membership testing instead of O(n) object comparison
    aod_ids = set()
    with alive_bar(
        len(aod), title="Building AOD ID index for deduplication", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            # Create unique identifier from available IDs
            if item.get("myanimelist"):
                aod_ids.add(("mal", item["myanimelist"]))
            elif item.get("anilist"):
                aod_ids.add(("anilist", item["anilist"]))
            elif item.get("title"):
                aod_ids.add(("title", item["title"]))
            bar()
    
    merged: list[dict[str, Any]] = []
    merged.extend(aod)

    # add missing items from old AOD data
    with alive_bar(
        len(aod_list), title="Reintroduce old list items", spinner=None
    ) as bar:  # type: ignore
        for item in aod_list:
            # Check if this item already exists using ID-based lookup
            item_id = None
            if item.get("myanimelist"):
                item_id = ("mal", item["myanimelist"])
            elif item.get("anilist"):
                item_id = ("anilist", item["anilist"])
            elif item.get("title"):
                item_id = ("title", item["title"])
            
            if item_id and item_id not in aod_ids:
                merged.append(item)
                aod_ids.add(item_id)  # Add to set to avoid duplicates
            bar()

    aod_list = merged
    pprint.print(
        Platform.OTAKOTAKU,
        Status.PASS,
        "Otak Otaku entries linked to MyAnimeList ID, unlinked data will be saved to otakotaku_unlinked.json.",
        "Total linked data:",
        f"{len(ot_fixed)},",
        "total unlinked data:",
        f"{len(unlinked)}",
    )
    with open("database/raw/otakotaku_unlinked.json", "w", encoding="utf-8") as file:
        json.dump(unlinked, file)
    return aod_list


def link_silveryasha_to_mal(
    silveryasha: list[dict[str, Any]], aod: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Link SilverYasha ID to MyAnimeList ID based similarity in title name over
    85% in fuzzy search

    :param silveryasha: SilverYasha data
    :type silveryasha: list[dict[str, Any]]
    :param aod: AOD data
    :type aod: list[dict[str, Any]]
    :return: Crude AniAPI data, requires refinement after the process
    :rtype: list[dict[str, Any]]
    """
    unlinked: list[dict[str, Any]] = []
    sy_fixed: list[dict[str, Any]] = []
    sy_dict: dict[str, Any] = {}
    aod_dict: dict[str, Any] = {}
    with alive_bar(
        len(aod), title="Translating AOD list to a dict with MAL ID", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            if item["myanimelist"]:
                aod_dict[f"{item['myanimelist']}"] = item
            else:
                aod_dict[item["title"]] = item
            bar()
    with alive_bar(
        len(silveryasha),
        title="Translating SilverYasha list to a dict with MAL ID",
        spinner=None,
    ) as bar:  # type: ignore
        for item in silveryasha:
            mal_id = item["myanimelist"]
            if mal_id:
                sy_dict[f"{mal_id}"] = {
                    "title": item["title"],
                    "silveryasha": item["silveryasha"],
                }
            else:
                sy_dict[item["title"]] = {
                    "title": item["title"],
                    "silveryasha": item["silveryasha"],
                }
            bar()
    with alive_bar(
        len(sy_dict), title="Linking SilverYasha ID to MyAnimeList ID", spinner=None
    ) as bar:  # type: ignore
        for mal_id, sy_item in sy_dict.items():
            if mal_id in aod_dict:
                aod_item: Union[dict[str, Any], None] = aod_dict.get(f"{mal_id}", None)
                if aod_item:
                    # add more data from silveryasha
                    sy_dat = {
                        "silveryasha": sy_item["silveryasha"],
                    }
                    aod_item.update(sy_dat)
                    sy_fixed.append(aod_item)
                else:
                    unlinked.append(sy_item)
            else:
                unlinked.append(sy_item)
            bar()
    # on unlinked, fuzzy search the title name (optimized)
    pprint.print(Platform.SILVERYASHA, Status.INFO, f"Optimized fuzzy matching {len(unlinked)} items")
    matches = _fuzzy_match_optimized(unlinked, aod, threshold=95)
    
    with alive_bar(
        len(matches), title="Processing fuzzy matches", spinner=None, disable=True
    ) as bar:  # type: ignore
        for item, aod_item in matches:
            sy_dat = {
                "silveryasha": item["silveryasha"],
            }
            aod_item.update(sy_dat)
            sy_fixed.append(aod_item)
            bar()
    # load manual link data
    with open("database/raw/silveryasha_manual.json", "r", encoding="utf-8") as file:
        manual_link: dict[str, int] = json.load(file)
    
    # Pre-index AOD by title for O(1) lookups
    aod_by_title = {item["title"]: item for item in aod}
    
    with alive_bar(
        len(manual_link), title="Insert manual mappings", spinner=None
    ) as bar:  # type: ignore
        for title, sy_id in manual_link.items():
            if isinstance(sy_id, list):
                sy_id = sy_id[0]
                override = True
            else:
                override = False
            if override is False and sy_id not in [
                item["silveryasha"] for item in unlinked
            ]:
                bar()
                continue
            
            # O(1) lookup instead of O(n) search
            aod_item = aod_by_title.get(title)
            if aod_item:
                sy_dat = {
                    "silveryasha": sy_id,
                }
                aod_item.update(sy_dat)
                sy_fixed.append(aod_item)
                # in unlinked, remove the item with the same id (optimized)
                unlinked = [item for item in unlinked if item["silveryasha"] != sy_id]
            bar()
    # remove if unlinked data is already linked (optimized with set)
    fixed_ids = {item["silveryasha"] for item in sy_fixed if "silveryasha" in item}
    original_count = len(unlinked)
    with alive_bar(
        original_count, title="Removing unrequired data from unlinked", spinner=None
    ) as bar:  # type: ignore
        unlinked = [item for item in unlinked if item["silveryasha"] not in fixed_ids]
        for _ in range(original_count):
            bar()
    aod_list: list[dict[str, Any]] = []
    with alive_bar(
        len(aod_dict), title="Translating AOD dict to a list", spinner=None
    ) as bar:  # type: ignore
        for _, value in aod_dict.items():
            if "silveryasha" not in value:
                value["silveryasha"] = None
            aod_list.append(value)
            bar()
    
    # Use set of IDs for O(1) membership testing instead of O(n) object comparison
    aod_ids = set()
    with alive_bar(
        len(aod), title="Building AOD ID index for deduplication", spinner=None
    ) as bar:  # type: ignore
        for item in aod:
            # Create unique identifier from available IDs
            if item.get("myanimelist"):
                aod_ids.add(("mal", item["myanimelist"]))
            elif item.get("anilist"):
                aod_ids.add(("anilist", item["anilist"]))
            elif item.get("title"):
                aod_ids.add(("title", item["title"]))
            bar()
    
    merged: list[dict[str, Any]] = []
    merged.extend(aod)

    # add missing items from old AOD data
    with alive_bar(
        len(aod_list), title="Reintroduce old list items", spinner=None
    ) as bar:  # type: ignore
        for item in aod_list:
            # Check if this item already exists using ID-based lookup
            item_id = None
            if item.get("myanimelist"):
                item_id = ("mal", item["myanimelist"])
            elif item.get("anilist"):
                item_id = ("anilist", item["anilist"])
            elif item.get("title"):
                item_id = ("title", item["title"])
            
            if item_id and item_id not in aod_ids:
                merged.append(item)
                aod_ids.add(item_id)  # Add to set to avoid duplicates
            bar()

    aod_list = merged
    pprint.print(
        Platform.SILVERYASHA,
        Status.PASS,
        "SilverYasha entry linked to MyAnimeList ID, unlinked data will be saved to silveryasha_unlinked.json.",
        "Total linked data:",
        f"{len(sy_fixed)},",
        "total unlinked data:",
        f"{len(unlinked)}",
    )
    with open("database/raw/silveryasha_unlinked.json", "w", encoding="utf-8") as file:
        json.dump(unlinked, file)
    return aod_list

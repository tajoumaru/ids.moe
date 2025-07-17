"""
Status file updater for the AnimeAPI.
Updates api/status.json with current statistics and metadata.
"""

import json
import os
from datetime import datetime
from typing import Dict

from generator.const import attribution, pprint
from generator.prettyprint import Platform, Status


class StatusUpdater:
    """Updates the API status file with current statistics."""

    def __init__(self, operations):
        self.operations = operations

    def update_status_file(self) -> None:
        """Update api/status.json with current statistics."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Updating status.json file...")

        try:
            # Get platform counts from database
            platform_counts = self._get_platform_counts()

            # Calculate total records
            total_records = self.operations.get_anime_count()

            # Get current timestamp
            now = datetime.now()

            # Update attribution data
            status_data = attribution.copy()
            status_data["updated"] = {
                "timestamp": int(now.timestamp()),
                "iso": now.isoformat(),
            }
            status_data["contributors"] = ["nattadasu", "tajoumaru"]
            status_data["counts"] = platform_counts
            status_data["counts"]["total"] = total_records

            # Write to both possible API locations
            api_paths = ["api/status.json", "status.json"]

            for path in api_paths:
                try:
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(path), exist_ok=True)

                    # Write status file
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(status_data, f, separators=(",", ": "))

                    pprint.print(Platform.SYSTEM, Status.PASS, f"Updated {path}")
                    break
                except FileNotFoundError:
                    # Try next path
                    continue
                except Exception as e:
                    pprint.print(
                        Platform.SYSTEM, Status.WARN, f"Failed to write {path}: {e}"
                    )
                    continue
            else:
                pprint.print(
                    Platform.SYSTEM,
                    Status.WARN,
                    "Could not write status.json to any location",
                )

        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.FAIL, f"Failed to update status file: {e}"
            )

    def _get_platform_counts(self) -> Dict[str, int]:
        """Get count of non-null entries for each platform."""
        platform_counts = {}

        # Define all platforms that should be counted
        platforms = [
            "anidb",
            "anilist",
            "animenewsnetwork",
            "animeplanet",
            "anisearch",
            "annict",
            "imdb",
            "kaize",
            "kitsu",
            "livechart",
            "myanimelist",
            "nautiljon",
            "notify",
            "otakotaku",
            "shikimori",
            "shoboi",
            "silveryasha",
            "simkl",
            "themoviedb",
            "trakt",
        ]

        try:
            # Get counts from database
            for platform in platforms:
                count = self.operations.get_platform_count(platform)
                platform_counts[platform] = count

        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.WARN, f"Error getting platform counts: {e}"
            )
            # Return zero counts if there's an error
            platform_counts = {platform: 0 for platform in platforms}

        return platform_counts

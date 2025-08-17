# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

# This file is part of 'ids.moe'. It is a derivative work of
# code from the 'animeApi' project by 'nattadasu'. The original license notices
# are preserved in the `NOTICE` file in the root of this repository.

import os
from typing import Any

from generator.prettyprint import PrettyPrint

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

if HAS_DOTENV and os.path.isfile(".env"):
    load_dotenv()


# Environment variables for scrapers
KAIZE_EMAIL = os.getenv("KAIZE_EMAIL")
"""User email for Kaize login"""
KAIZE_PASSWORD = os.getenv("KAIZE_PASSWORD")
"""User password for Kaize login"""

# GitHub Actions detection
GITHUB_DISPATCH = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
"""Whether the script is running from GitHub Actions workflow_dispatch event"""

# GitHub API token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
"""GitHub API token for authenticated requests"""

# PostgreSQL database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
"""PostgreSQL database URL for serverless PostgreSQL connection"""


# Process PostgreSQL URL to ensure proper format
def process_database_url(url: str | None = None) -> str:
    """Process PostgreSQL URL to ensure proper format for psycopg2."""
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")

    # For synchronous PostgreSQL, we can use the URL as-is
    # psycopg2 supports sslmode parameter directly
    return url


# Process the URL
DATABASE_URL = process_database_url(DATABASE_URL)

# Cache configuration
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
"""Cache directory for downloaded files"""

# Scraper cache expiry
SCRAPER_CACHE_EXPIRY_DAYS = int(os.getenv("SCRAPER_CACHE_EXPIRY_DAYS", "14"))
"""Number of days to cache scraper data before re-running"""

# Cloudflare Workers KV configuration
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
"""Cloudflare account ID"""
CLOUDFLARE_KV_NAMESPACE_ID = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")
"""Cloudflare Workers KV namespace ID"""
CLOUDFLARE_AUTH_TOKEN = os.getenv("CLOUDFLARE_AUTH_TOKEN")
"""Cloudflare API token with Workers KV permissions"""

pprint = PrettyPrint()
"""PrettyPrint class instance"""

attribution: dict[str, Any] = {
    "mainrepo": "https://github.com/tajoumaru/ids.moe",
    "updated": {"timestamp": 0, "iso": ""},
    "contributors": [""],
    "sources": [
        "nattadasu/animeApikawaiioverflow/arm",
        "manami-project/anime-offline-database",
        "rensetsu/db.rensetsu.public-dump",
        "rensetsu/db.trakt.anitrakt",
        "https://kaize.io",
        "https://nautiljon.com",
        "https://otakotaku.com",
    ],
    "license": "AGPL-3.0-only",
    "website": "https://ids.moe",
    "counts": {
        "anidb": 0,
        "anilist": 0,
        "animenewsnetwork": 0,
        "animeplanet": 0,
        "anisearch": 0,
        "annict": 0,
        "imdb": 0,
        "kaize": 0,
        "kitsu": 0,
        "livechart": 0,
        "myanimelist": 0,
        "nautiljon": 0,
        "notify": 0,
        "otakotaku": 0,
        "shikimori": 0,
        "shoboi": 0,
        "silveryasha": 0,
        "simkl": 0,
        "themoviedb": 0,
        "trakt": 0,
        "total": 0,
    },
    "endpoints": {
        "$comment": "The endpoints are stated in Python regex format. Platform aliases supported for direct lookup for platform specific endpoints (see ?P<alias> in regex).",
        "anidb": r"/(?P<alias>anidb)/(?P<media_id>\d+)",
        "anilist": r"/(?P<alias>anilist)/(?P<media_id>\d+)",
        "animeapi_dump": r"/(anime(?:a|A)pi|aa)(?:\\\.json)?",
        "animeapi_tsv": r"/(anime(?:a|A)pi|aa).tsv",
        "animenewsnetwork": r"(?P<alias>animenewsnetwork)/(?P<media_id>\d+)",
        "animeplanet": r"/(?P<alias>animeplanet)/(?P<media_id>[\w\-]+)",
        "anisearch": r"/(?P<alias>anisearch)/(?P<media_id>\d+)",
        "annict": r"/(?P<alias>annict)/(?P<media_id>\d+)",
        "heartbeat": r"/(heartbeat|ping)",
        "imdb": r"/(?P<alias>imdb)/(?P<media_id>tt[\d]+)",
        "kaize": r"/(?P<alias>kaize)/(?P<media_id>[\w\-]+)",
        "kitsu": r"/(?P<alias>kitsu)/(?P<media_id>\d+)",
        "livechart": r"/(?P<alias>livechart)/(?P<media_id>\d+)",
        "myanimelist": r"/(?P<alias>myanimelist)/(?P<media_id>\d+)",
        "nautiljon": r"/(?P<alias>nautiljon)/(?P<media_id>[\w\+!\-_\(\)\[\]]+)",
        "notify": r"/(?P<alias>notify)/(?P<media_id>[\w\-_]+)",
        "otakotaku": r"/(?P<alias>otakotaku)/(?P<media_id>\d+)",
        "platform_dump": r"/(?P<alias>[\w\-]+)(?:\\\.json)?",
        "redirect": r"/(redirect|rd)",
        "repo": r"/",
        "schema": r"/schema(?:\\\.json)?",
        "shikimori": r"/(?P<alias>shikimori)/(?P<media_id>\d+)",
        "shoboi": r"/(?P<alias>shoboi)/(?P<media_id>\d+)",
        "silveryasha": r"/(?P<alias>silveryasha)/(?P<media_id>\d+)",
        "simkl": r"/(?P<alias>simkl)/(?P<media_id>\d+)",
        "status": r"/status",
        "syobocal": r"/(?P<alias>syobocal)/(?P<media_id>\d+)",
        "themoviedb": r"/(?P<alias>themoviedb)/movie/(?P<media_id>\d+)",
        "trakt": r"/(?P<alias>trakt)/(?P<media_type>show|movie)(s)?/(?P<media_id>\d+)(?:/season(s)?/(?P<season_id>\d+))?",
        "updated": r"/updated",
    },
}
"""Attribution data"""

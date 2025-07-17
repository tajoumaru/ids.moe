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
KAIZE_XSRF_TOKEN = os.getenv("KAIZE_XSRF_TOKEN")
"""Kaize XSRF token"""
KAIZE_SESSION = os.getenv("KAIZE_SESSION")
"""Kaize session cookie"""
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

# Turso/SQLite database configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "anime_data.db")
"""Turso database URL (can be local file or remote URL)"""
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
"""Turso authentication token (only for remote connections)"""


# Process Turso URL to ensure proper format
def process_turso_url(url: str, auth_token: str | None = None) -> str:
    """Process Turso URL to ensure proper format."""
    # Remove protocol if present
    if url.startswith("libsql://"):
        url = url[9:]
    elif url.startswith("sqlite://"):
        url = url[9:]
    elif url.startswith("sqlite+libsql://"):
        url = url[16:]

    # Check if it's a remote URL
    is_remote = ".turso.io" in url or ".aws" in url or "://" in url

    # Build proper connection string
    if is_remote:
        connection_url = f"sqlite+libsql://{url}"
        # Add secure parameter if auth token is provided
        if auth_token and "?secure=true" not in connection_url:
            connection_url += "?secure=true"
    else:
        # Local file
        connection_url = f"sqlite+libsql:///{url}"

    return connection_url


# Process the URL
TURSO_DATABASE_URL = process_turso_url(
    TURSO_DATABASE_URL or "anime_data.db", TURSO_AUTH_TOKEN
)

# Cache configuration
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
"""Cache directory for downloaded files"""

# Scraper cache expiry
SCRAPER_CACHE_EXPIRY_DAYS = int(os.getenv("SCRAPER_CACHE_EXPIRY_DAYS", "14"))
"""Number of days to cache scraper data before re-running"""

# Redis configuration - Upstash
KV_REST_API_URL = os.getenv("KV_REST_API_URL")
"""Upstash Redis REST API URL"""
KV_REST_API_TOKEN = os.getenv("KV_REST_API_TOKEN")
"""Upstash Redis REST API token"""

# Redis configuration - Standard Redis
REDIS_URL = os.getenv("REDIS_URL")
"""Redis connection URL"""

# Redis connection components (alternative to URL)
REDIS_HOST = os.getenv("REDIS_HOST")
"""Redis host"""
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379")) if os.getenv("REDIS_PORT") else 6379
"""Redis port"""
REDIS_USER = os.getenv("REDIS_USER")
"""Redis username"""
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
"""Redis password"""
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
"""Redis database number (only used with component architecture)"""
REDIS_SSL = os.getenv("REDIS_SSL", "").lower() in ["true", "1", "yes"]
"""Redis SSL/TLS enabled"""
REDIS_SSL_CERT_PATH = os.getenv("REDIS_SSL_CERT_PATH")
"""Path to Redis SSL certificate"""
REDIS_SSL_KEY_PATH = os.getenv("REDIS_SSL_KEY_PATH")
"""Path to Redis SSL key"""
REDIS_SSL_CA_PATH = os.getenv("REDIS_SSL_CA_PATH")
"""Path to Redis SSL CA certificate"""

# Build Redis URL from components if URL not provided
if not REDIS_URL and REDIS_HOST:
    # Build URL from components
    auth_part = ""
    if REDIS_USER and REDIS_PASSWORD:
        auth_part = f"{REDIS_USER}:{REDIS_PASSWORD}@"
    elif REDIS_PASSWORD:
        auth_part = f":{REDIS_PASSWORD}@"

    protocol = "rediss" if REDIS_SSL else "redis"
    REDIS_URL = f"{protocol}://{auth_part}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

pprint = PrettyPrint()
"""PrettyPrint class instance"""

attribution: dict[str, Any] = {
    "mainrepo": "https://github.com/nattadasu/animeApi/tree/v3",
    "updated": {"timestamp": 0, "iso": ""},
    "contributors": [""],
    "sources": [
        "kawaiioverflow/arm",
        "manami-project/anime-offline-database",
        "rensetsu/db.rensetsu.public-dump",
        "rensetsu/db.trakt.anitrakt",
        "https://kaize.io",
        "https://nautiljon.com",
        "https://otakotaku.com",
    ],
    "license": "AGPL-3.0-only AND MIT AND CC0-1.0+",
    "website": "https://animeapi.my.id",
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

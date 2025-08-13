# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IDS.moe is a high-performance anime ID mapping API that provides cross-platform anime database ID relationships. It maps anime IDs between 21 different platforms (MyAnimeList, AniList, AniDB, Kitsu, IMDB, etc.).

## Development Commands

### Python Data Pipeline
```bash
# Run the entire data pipeline
uv run generator

# Individual pipeline stages
uv run generator download    # Download data from sources
uv run generator process     # Process and map anime data
uv run generator ingest      # Ingest to Redis/KV
uv run generator status      # Check database status
uv run generator prune       # Clean up old data

# Type checking and linting
uv run ty                    # Run type checking
uv run ruff check            # Run linting
uv run ruff format           # Format Python code
```

### Local Development Setup
```bash
# Start local databases (PostgreSQL and DragonflyDB)
docker compose up -d

# Install Python dependencies
uv sync

# Run tests (if any exist)
uv run pytest
```

### Go API Development
```bash
# Run Go API locally (from api/ directory)
cd api && go run index.go

# Build Go module
cd api && go build
```

## Architecture

### Two-Component System
1. **API Layer** (`api/index.go`): Go-based Vercel Function serving HTTP requests with Redis caching
2. **Data Pipeline** (`generator/`): Python-based ETL pipeline that updates anime mappings

### Data Flow
1. **Download Phase**: Fetches data from GitHub repos and web scrapers
2. **Processing Phase**: Maps relationships between platform IDs using fuzzy matching
3. **Ingestion Phase**: Stores in Redis as two-tier structure:
   - Platform ID → Internal ID (300k+ keys)
   - Internal ID → Full anime data (single key per anime)

### Key Files
- `generator/pipeline.py`: Main orchestration of data pipeline
- `generator/processor.py`: Core mapping logic and fuzzy matching
- `generator/models.py`: SQLAlchemy models for PostgreSQL storage
- `generator/scrapers/`: Platform-specific web scrapers (Kaize, Nautiljon, Otak Otaku)
- `api/index.go`: API server handling all HTTP routes

## Database Configuration

### Environment Variables Required
```bash
# PostgreSQL (for pipeline processing)
DATABASE_URL=postgresql://user:pass@host/db

# Redis/Upstash (for API serving)
KV_REST_API_URL=https://...
KV_REST_API_TOKEN=...

# Optional scraper authentication
KAIZE_COOKIE=...  # For Kaize scraper
```

### Redis Key Structure
- `{platform}:{id}` → Internal UUID (e.g., `mal:1` → `uuid-123`)
- `anime:{uuid}` → Full anime data JSON with all platform mappings

## API Routes

- `GET /{platform}/{id}` - Get all platform IDs for an anime
- `GET /status` - Database statistics and platform counts
- `GET /heartbeat` - Health check with response time
- `GET /redirect?from={platform}&to={platform}&id={id}` - Platform redirects
- `GET /schema` - API schema documentation

## Platform Aliases

The API supports shortened platform names:
- `mal` → `myanimelist`
- `al` → `anilist`
- `ap` → `anime-planet`
- `kt` → `kitsu`
- `tvdb` → `thetvdb`
- Full list in `api/index.go` platformAliases map

## Testing & Quality

Pre-commit hooks (via lefthook) automatically run:
- Type checking with `ty`
- Code formatting with `ruff format`
- Linting with `ruff check`

## Deployment

- **API**: Deployed to Vercel Functions (automatic on push to main)
- **Pipeline**: Runs nightly via GitHub Actions workflow
- **Database Updates**: Incremental using SHA-256 change detection

## Important Patterns

### Error Handling
- API returns structured JSON errors with appropriate HTTP status codes
- Pipeline uses comprehensive logging and continues on partial failures

### Performance Optimizations
- Two-tier Redis structure minimizes key lookups
- Fuzzy matching uses thefuzz library (1.5x faster than fuzzywuzzy)
- Incremental updates only process changed anime

### Data Sources
- `anime-offline-database` (GitHub)
- ARM project mappings (GitHub)
- Web scrapers for Kaize, Nautiljon, Otak Otaku (rate-limited)

## Licensing Notes

- Main codebase: AGPL-3.0-only
- Contains MIT-licensed components from original AnimeAPI (see NOTICE.md)
- Attribution required for derivative works
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AnimeAPI is a RESTful API that provides anime relation mapping across multiple anime databases. The project aggregates data from 17+ sources including MyAnimeList, AniList, Kitsu, and many others to create comprehensive cross-platform anime ID mappings.

## Architecture

### Main Components

- **`api/`** - Flask-based REST API server (`api/index.py:23`)
  - Serves JSON responses for anime mappings
  - Handles platform aliases and redirects
  - Deployed on Vercel via `vercel.json`

- **`generator/`** - Data collection and processing pipeline (`generator/main.py:42`)
  - Scrapes and fetches data from multiple anime databases
  - Combines and normalizes data from various sources
  - Outputs unified JSON files with cross-platform mappings

- **`database/raw/`** - Raw scraped data storage
  - JSON files from individual platforms
  - Used as input for the generator pipeline

## Development Commands

This project uses uv for Python dependency management:

```bash
# Install dependencies
uv sync

# Run the API server locally
cd api && python -m flask run

# Run the data generator
cd generator && python main.py

# Run API as module
python -m api

# Run generator as module  
python -m generator
```

## Data Flow

1. **Collection**: `generator/` scripts fetch data from multiple anime databases
2. **Processing**: Data is normalized and linked via MyAnimeList IDs as the primary key
3. **Output**: Combined JSON files are generated for API consumption
4. **Serving**: Flask API in `api/` serves the processed data via REST endpoints

## Key Platform Integrations

The generator includes specialized scrapers for:
- **Kaize** (`generator/kaize.py`) - Requires authentication credentials
- **Nautiljon** (`generator/nautiljon.py`) - French anime database
- **Otak Otaku** (`generator/otakotaku.py`) - Indonesian anime database

Authentication for Kaize requires environment variables:
- `KAIZE_SESSION`, `KAIZE_XSRF_TOKEN`, `KAIZE_EMAIL`, `KAIZE_PASSWORD`

## API Structure

The API supports multiple endpoints for different data formats:
- Individual anime lookups: `/:platform/:id`
- Platform-specific dumps: `/:platform.json`
- Full database export: `/animeApi.json` or `/aa.json`
- TSV export: `/animeApi.tsv`
- Status and metadata: `/status`

Platform aliases are extensively supported - see `PLATFORM_SYNONYMS` in `api/index.py:28`.

## Licensing

- Primary code: AGPL-3.0-only
- Scraper scripts for Kaize, Nautiljon, Otak Otaku: MIT
- Raw database files: CC0
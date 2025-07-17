# AnimeAPI Pipeline Usage Guide

## Overview

The AnimeAPI pipeline is a comprehensive data processing system that downloads, processes, and syncs anime data from multiple sources to a SQLite database and Redis/KV store.

## CLI Commands

### Basic Usage

```bash
uv run generator [command] [options]
# OR
python -m generator [command] [options]
```

### Available Commands

#### `full` - Run Complete Pipeline (Default)
Executes all three phases: download, process, and KV sync. This is the default command when no command is specified.

```bash
uv run generator full
uv run generator  # Same as above (default)
uv run generator full --turso-url your-db.turso.io --cache-dir /custom/cache
```

#### `download` - Download Phase Only
Downloads data from GitHub and runs web scrapers. Does not process or sync data.

```bash
uv run generator download
uv run generator download --ignore-cache  # Force re-download all files
uv run generator download --cache-dir /custom/cache
```

#### `process` - Processing Phase Only
Processes downloaded cache files and updates the database. Does not download or sync to KV store.

```bash
uv run generator process
uv run generator process --turso-url your-db.turso.io --cache-dir /custom/cache
```

#### `ingest` - KV Ingestion Phase Only
Syncs pending database changes to the Redis/KV store. Does not download or process data.

```bash
uv run generator ingest
uv run generator ingest --force-overwrite-all  # Rebuild entire KV store
uv run generator ingest --redis-host localhost --redis-port 6379
```

#### `status` - Check Pipeline Status
Displays current database statistics and sync information.

```bash
uv run generator status
uv run generator status --turso-url your-db.turso.io
```

#### `prune` - Data Cleanup Commands
Remove data with confirmation prompts.

```bash
uv run generator prune cache     # Remove all cached files
uv run generator prune turso     # Clear entire database
uv run generator prune redis     # Clear Redis/KV store
uv run generator prune all       # Remove all data (requires double confirmation)
```

### Command-Line Options

#### Database Configuration
| Option | Description | Default |
|--------|-------------|---------|
| `--turso-url` | Database URL (local file or Turso remote) | From `TURSO_DATABASE_URL` env var |
| `--turso-token` | Turso authentication token | From `TURSO_AUTH_TOKEN` env var |

#### Cache Configuration
| Option | Description | Default |
|--------|-------------|---------|
| `--cache-dir` | Directory for cached JSON files | From `CACHE_DIR` env var |

#### Redis Configuration (Regular Redis)
| Option | Description | Default |
|--------|-------------|---------|
| `--redis-url` | Redis connection URL | From `REDIS_URL` env var |
| `--redis-host` | Redis host | From `REDIS_HOST` env var |
| `--redis-port` | Redis port | From `REDIS_PORT` env var |
| `--redis-user` | Redis username | From `REDIS_USER` env var |
| `--redis-password` | Redis password | From `REDIS_PASSWORD` env var |
| `--redis-db` | Redis database number | From `REDIS_DB` env var |
| `--redis-ssl` | Use Redis SSL/TLS | From `REDIS_SSL` env var |

#### Redis Configuration (Upstash)
| Option | Description | Default |
|--------|-------------|---------|
| `--upstash-url` | Upstash Redis REST API URL | From `KV_REST_API_URL` env var |
| `--upstash-token` | Upstash Redis REST API token | From `KV_REST_API_TOKEN` env var |

#### Special Flags
| Option | Description | Available For |
|--------|-------------|---------------|
| `--ignore-cache` | Ignore cache and re-download all files | `download` only |
| `--force-overwrite-all` | Rebuild entire KV store from scratch | `ingest` only |
| `--no-env-check` | Skip environment variable validation | All commands |

## Environment Variables

All configuration is primarily done through environment variables. Command-line arguments are secondary overrides.

### Required Environment Variables

#### Database Configuration
| Variable | Description | Example |
|----------|-------------|---------|
| `TURSO_DATABASE_URL` | Database URL (local file or remote) | `anime_data.db` or `your-db.turso.io` |
| `TURSO_AUTH_TOKEN` | Authentication token (for remote Turso only) | `your-auth-token` |

#### Cache Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `CACHE_DIR` | Cache directory for downloaded files | `cache` |
| `SCRAPER_CACHE_EXPIRY_DAYS` | Days to cache scraper data | `14` |

### Optional Environment Variables

#### GitHub API (Recommended)
| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub personal access token for higher API rate limits | No |

#### Kaize Scraper Authentication
All four variables must be set to enable Kaize data collection:

| Variable | Description | Required |
|----------|-------------|----------|
| `KAIZE_SESSION` | Kaize session cookie | For Kaize data* |
| `KAIZE_XSRF_TOKEN` | Kaize XSRF token | For Kaize data* |
| `KAIZE_EMAIL` | Kaize login email | For Kaize data* |
| `KAIZE_PASSWORD` | Kaize login password | For Kaize data* |

*Required only if you want to fetch Kaize data. The pipeline will work without these.

#### Redis/KV Store Configuration

Configure **either** regular Redis or Upstash Redis (not both):

##### Option 1: Regular Redis (via URL)
| Variable | Description | Required |
|----------|-------------|----------|
| `REDIS_URL` | Complete Redis connection URL | For KV sync** |

##### Option 2: Regular Redis (via Components)
| Variable | Description | Required |
|----------|-------------|----------|
| `REDIS_HOST` | Redis host | For KV sync** |
| `REDIS_PORT` | Redis port | No (default: 6379) |
| `REDIS_USER` | Redis username | No |
| `REDIS_PASSWORD` | Redis password | No |
| `REDIS_DB` | Redis database number | No (default: 0) |
| `REDIS_SSL` | Use SSL/TLS (`true`/`false`) | No (default: false) |
| `REDIS_SSL_CERT_PATH` | Path to SSL certificate | No |
| `REDIS_SSL_KEY_PATH` | Path to SSL key | No |
| `REDIS_SSL_CA_PATH` | Path to SSL CA certificate | No |

##### Option 3: Upstash Redis
| Variable | Description | Required |
|----------|-------------|----------|
| `KV_REST_API_URL` | Upstash Redis REST API URL | For KV sync** |
| `KV_REST_API_TOKEN` | Upstash Redis REST API token | For KV sync** |

**One Redis configuration is required for KV ingestion. Without Redis, the pipeline will process data but skip KV store synchronization.

### Database URL Format

The `TURSO_DATABASE_URL` supports multiple formats:

- **Local SQLite**: `anime_data.db` or `./path/to/database.db`
- **Remote Turso**: `your-db.turso.io` or `your-db.aws-eu-west-1.turso.io`
- **With protocol**: `sqlite://anime_data.db` or `libsql://your-db.turso.io`

The system automatically:
- Adds `sqlite+libsql://` protocol prefix
- Adds `?secure=true` parameter for remote connections with auth tokens
- Handles both local and remote databases seamlessly

## Example Workflows

### First-Time Setup

```bash
# Set up environment variables
export TURSO_DATABASE_URL="anime_data.db"
export CACHE_DIR="cache"
export GITHUB_TOKEN="ghp_your_token_here"
export REDIS_URL="redis://localhost:6379"

# Run full pipeline
uv run generator full
```

### Production with Turso Cloud

```bash
# Set Turso credentials
export TURSO_DATABASE_URL="your-db.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
export KV_REST_API_URL="https://your-redis.upstash.io"
export KV_REST_API_TOKEN="your-upstash-token"

# Run full pipeline
uv run generator full
```

### Development Workflow

```bash
# Download latest data
uv run generator download

# Process the data
uv run generator process

# Sync to KV store
uv run generator ingest

# Check status
uv run generator status
```

### Force Refresh Everything

```bash
# Force re-download all files and rebuild KV store
uv run generator download --ignore-cache
uv run generator process
uv run generator ingest --force-overwrite-all
```

### Incremental Updates

```bash
# Only process changes (normal operation)
uv run generator full

# Or just sync pending changes
uv run generator ingest
```

### Maintenance

```bash
# Clean up old cache files
uv run generator prune cache

# Reset entire system (use with caution)
uv run generator prune all
```

## Pipeline Phases

1. **Download Phase**: Fetches data from GitHub and runs web scrapers
2. **Processing Phase**: Extracts, matches, and merges anime data into database
3. **KV Ingestion Phase**: Syncs processed data to Redis/KV store for API access

## Output Information

The pipeline provides detailed progress information:

- Environment variable validation
- Real-time progress for each phase
- Performance metrics (time taken, records processed)
- File download and processing statistics
- KV store synchronization results
- Error messages with debugging information

## Troubleshooting

### Common Issues

- **"Missing Redis credentials"**: Set either `REDIS_URL`/`REDIS_HOST` or `KV_REST_API_URL`/`KV_REST_API_TOKEN`
- **"No such file or directory"**: Ensure `TURSO_DATABASE_URL` points to a valid path or Turso instance
- **"Resource temporarily unavailable"**: System resource limit reached, try closing other applications
- **"Too many SQL variables"**: Should be automatically handled with batching
- **Rate limiting**: Set `GITHUB_TOKEN` to avoid GitHub API limits

### Performance Tips

- Use `GITHUB_TOKEN` to avoid API rate limits
- Use `--ignore-cache` sparingly to avoid unnecessary downloads
- Use `--force-overwrite-all` only when KV store is corrupted
- Run `prune cache` periodically to clean up old files

### Development Mode

For development, you can skip environment checks:

```bash
uv run generator full --no-env-check
```

This is useful when testing with minimal configuration.

# AnimeAPI Pipeline Usage Guide

## Overview

The AnimeAPI pipeline is a comprehensive data processing system that downloads, processes, and syncs anime data from multiple sources to a PostgreSQL database and Redis/KV store.

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
uv run generator full --database-url postgresql://user:pass@host:5432/db --cache-dir /custom/cache
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
uv run generator process --database-url postgresql://user:pass@host:5432/db --cache-dir /custom/cache
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
uv run generator status --database-url postgresql://user:pass@host:5432/db
```

#### `prune` - Data Cleanup Commands
Remove data with confirmation prompts.

```bash
uv run generator prune cache     # Remove all cached files
uv run generator prune database  # Clear entire database
uv run generator prune redis     # Clear Redis/KV store
uv run generator prune all       # Remove all data (requires double confirmation)
```

### Command-Line Options

#### Database Configuration
| Option | Description | Default |
|--------|-------------|---------|
| `--database-url` | PostgreSQL database URL | From `DATABASE_URL` env var |

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
| `DATABASE_URL` | PostgreSQL database URL | `postgresql://user:pass@localhost:5432/animeapi` |

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

The `DATABASE_URL` must be a PostgreSQL connection string:

**Format**: `postgresql://username:password@host:port/database`

**Examples**:
- **Local PostgreSQL**: `postgresql://user:pass@localhost:5432/animeapi`
- **With SSL**: `postgresql://user:pass@host:5432/animeapi?sslmode=require`
- **Serverless PostgreSQL**: `postgresql://user:pass@serverless-db.example.com:5432/animeapi?sslmode=require`

### Recommended Serverless PostgreSQL Providers

1. **Neon** (https://neon.tech)
   ```
   DATABASE_URL=postgresql://user:pass@ep-xxx-xxx.us-east-1.aws.neon.tech/animeapi?sslmode=require
   ```

2. **Supabase** (https://supabase.com)
   ```
   DATABASE_URL=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres?sslmode=require
   ```

3. **Vercel Postgres** (https://vercel.com/storage/postgres)
   ```
   DATABASE_URL=postgresql://user:pass@ep-xxx-xxx.us-east-1.postgres.vercel-storage.com/animeapi?sslmode=require
   ```

4. **Railway** (https://railway.app)
   ```
   DATABASE_URL=postgresql://postgres:pass@containers-us-west-xxx.railway.app:5432/railway
   ```

5. **AWS RDS Serverless** (https://aws.amazon.com/rds/serverless/)
   ```
   DATABASE_URL=postgresql://user:pass@cluster.cluster-xxx.us-east-1.rds.amazonaws.com:5432/animeapi
   ```

## Example Workflows

### First-Time Setup

```bash
# Set up environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/animeapi"
export CACHE_DIR="cache"
export GITHUB_TOKEN="ghp_your_token_here"
export REDIS_URL="redis://localhost:6379"

# Run full pipeline
uv run generator full
```

### Production with Serverless PostgreSQL

```bash
# Set PostgreSQL and Redis credentials
export DATABASE_URL="postgresql://user:pass@ep-xxx-xxx.us-east-1.aws.neon.tech/animeapi?sslmode=require"
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
2. **Processing Phase**: Extracts, matches, and merges anime data into PostgreSQL database
3. **KV Ingestion Phase**: Syncs processed data to Redis/KV store for API access

## Performance Improvements

The migration to PostgreSQL provides significant performance benefits:

- **Faster Bulk Operations**: PostgreSQL handles large datasets much better than SQLite
- **Async Operations**: All database operations are now asynchronous with connection pooling
- **Larger Batch Sizes**: Increased from 999 (SQLite limit) to 1000+ records per batch
- **Better Concurrency**: Connection pooling allows multiple operations simultaneously
- **Serverless Ready**: Works with all major serverless PostgreSQL providers

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

- **"PostgreSQL DATABASE_URL is required"**: Set the `DATABASE_URL` environment variable
- **"Missing Redis credentials"**: Set either `REDIS_URL`/`REDIS_HOST` or `KV_REST_API_URL`/`KV_REST_API_TOKEN`
- **"Connection refused"**: Ensure PostgreSQL server is running and accessible
- **"SSL required"**: Add `?sslmode=require` to your DATABASE_URL for serverless providers
- **Rate limiting**: Set `GITHUB_TOKEN` to avoid GitHub API limits

### Performance Tips

- Use a serverless PostgreSQL provider for best performance
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

## Migration from SQLite/Turso

If you're migrating from the previous SQLite/Turso setup:

1. **Update dependencies**: `pip install -e .` (asyncpg will be installed automatically)
2. **Set DATABASE_URL**: Replace `TURSO_DATABASE_URL` with `DATABASE_URL`
3. **Run migration**: The first run will automatically create PostgreSQL tables
4. **Better performance**: Enjoy significantly faster bulk operations!
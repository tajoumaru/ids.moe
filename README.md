# ids.moe - High-Performance Anime ID Mapping API

A blazingly fast RESTful API that provides anime relation mapping across multiple anime databases. Complete rewrite of the original [nattadasu/animeApi](https://github.com/nattadasu/animeapi) with significant performance improvements and modern infrastructure.

This project is forked from [nattadasu/animeApi](https://github.com/nattadasu/animeapi) and transformed with a completely rewritten data pipeline and API architecture optimized for speed and scalability.

## 🚀 Key Improvements

- **Much Faster API Response**: Go-based API with Redis KV store
- **Much Faster Data Processing**: PostgreSQL with `COPY FROM` insertions and multiprocessing
- **Intelligent Caching**: Only downloads & processes changed data with hash-based detection
- **Space Efficient**: Two-tier Redis structure (300k ID mappings → internal IDs → full objects)
- **Serverless Ready**: Meant to deploy with Vercel, Neon & Upstash out of the box
- **Modern Pipeline**: GitHub Actions with dependency caching and incremental updates

## 🏗️ Architecture

### API Layer (Go)
- **Runtime**: Go with Redis client
- **Hosting**: Vercel Functions
- **Response Time**: ~100ms typical response

### Data Pipeline (Python)
- **Database**: PostgreSQL (remote or local)
- **Cache**: Redis/Upstash KV (remote or local)
- **Processing**: Many operations multithreaded and optimized
- **Scheduling**: GitHub Actions (nightly updates to the db and kvstore)

### Storage Strategy
1. **Platform ID → Internal ID**: ~300k Redis keys (e.g., `anilist_156` → `466`)
2. **Internal ID → Full Data**: Single Redis key per anime with all platform IDs
   - Two tiered approach is both fast and space efficient with no duplicate data
3. **Change Detection**: SHA-256 hashes stored in PostgreSQL for incremental updates

## 📊 Supported Platforms

|           Platform |  2K   | Aliases                                                                                         |
| -----------------: | :---: | ----------------------------------------------------------------------------------------------- |
|            `anidb` | `ad`  | `adb`, `anidb.net`                                                                              |
|          `anilist` | `al`  | `anilist.co`                                                                                    |
| `animenewsnetwork` | `an`  | `ann`, `animenewsnetwork.com`                                                                   |
|      `animeplanet` | `ap`  | `anime-planet.com` `anime-planet`, `animeplanet.com`                                            |
|        `anisearch` | `as`  | `anisearch.com`, `anisearch.de`, `anisearch.it`, `anisearch.es`, `anisearch.fr`, `anisearch.jp` |
|           `annict` | `ac`  | `anc`, `act`, `annict.com`, `annict.jp`, `en.annict.com`                                        |
|             `imdb` | `im`  | `imdb.com`                                                                                      |
|            `kaize` | `kz`  | `kaize.io`                                                                                      |
|            `kitsu` | `kt`  | `kts`, `kitsu.io`, `kitsu.app`                                                                  |
|        `livechart` | `lc`  | `livechart.me`                                                                                  |
|      `myanimelist` | `ma`  | `mal`, `myanimelist.net`                                                                        |
|        `nautiljon` | `nj`  | `ntj`, `nautiljon.com`                                                                          |
|           `notify` | `nf`  | `ntf`, `ntm`, `notifymoe`, `notify.moe`                                                         |
|        `otakotaku` | `oo`  | `otakotaku.com`                                                                                 |
|        `shikimori` | `sh`  | `shiki`, `shk`, `shikimori.me`, `shikimori.one`, `shikimori.org`                                |
|           `shoboi` | `sb`  | `shb`, `syb`, `shobocal`, `syoboi`, `syobocal`, `cal.syoboi.jp`                                 |
|      `silveryasha` | `sy`  | `dbti`, `db.silveryasha.id`, `db.silveryasha.web.id`                                            |
|            `simkl` | `sm`  | `smk`, `simkl.com`, `animecountdown`, `animecountdown.com`                                      |
|       `themoviedb` | `tm`  | `tmdb`, `themoviedb.org`                                                                        |
|            `trakt` | `tr`  | `trk`, `trakt.tv`                                                                               |

## 🔧 API Usage

### Base URL
```
https://ids.moe
```

### Get Anime Relations
```http
GET /{platform}/{id}
```

**Example**: Get all platform IDs for MyAnimeList ID 1 (Cowboy Bebop)
```
curl https://ids.moe/mal/1
```

**Response**:
```json
{
  "title": "Cowboy Bebop",
  "anidb": 23,
  "anilist": 1,
  "animenewsnetwork": 13,
  "animeplanet": "cowboy-bebop",
  "anisearch": 1572,
  "annict": 360,
  "imdb": null,
  "kaize": "cowboy-bebop",
  "kaize_id": 265,
  "kitsu": 1,
  "livechart": 3418,
  "myanimelist": 1,
  "nautiljon": null,
  "nautiljon_id": null,
  "notify": "Tk3ccKimg",
  "otakotaku": 1149,
  "shikimori": 1,
  "shoboi": 538,
  "silveryasha": 2652,
  "simkl": 37089,
  "themoviedb": null,
  "trakt": 30857,
  "trakt_type": "shows",
  "trakt_season": 1
}
```

### Status and Statistics
```http
GET /status
```

### Test latency
```http
GET /heartbeat
```

`{"status":"OK","code":200,"request_time":"0.129s","response_time":"0.129s","request_epoch":1752876928}`
> ^ The delta between request_time and response_time is the processing time. In my testing always 0.000s\
> I've found that the only latency is the network request latency to Vercel. The rest is instant.


### Redirect to Platform
```http
GET /redirect?platform=myanimelist&mediaid=1&target=anilist
```

### Platform Aliases
All platforms support multiple aliases (case-insensitive):
- `myanimelist` → `mal`, `ma`
- `anilist` → `al`
- `animeplanet` → `ap`, `anime-planet`
- And many more...

## 🚀 Deploy Your Own Instance

### 1. Fork the Repository
1. Just press the "Fork" button in the top right
2. GitHub will guide you through the rest

### 2. Set up Vercel
1. Go to [Vercel](https://vercel.com)
2. Create an account and connect your github account
3. Import your personal fork
4. Deploy it (the api will not work yet)

### 3. Add Database & Redis
In Vercel Storage tab:
- Add **Neon PostgreSQL** database
- Add **Upstash Redis** instance

Both work perfectly on free tiers for this use case.

- **Afterwards redeploy the Vercel deployment**

### 4. Configure Secrets
Add these GitHub repository secrets:

**Required**:
- `DATABASE_URL` - PostgreSQL connection string from Neon
- `KV_REST_API_URL` - Upstash Redis URL
- `KV_REST_API_TOKEN` - Upstash Redis token
> ^ All three can be found on vercel in the storage settings

**Optional but recommended**:
- `KAIZE_EMAIL` - Kaize account email (kaize scraper is skipped otherwise)
- `KAIZE_PASSWORD` - Kaize account password (kaize scraper is skipped otherwise)
- `GITHUB_TOKEN` - GitHub Personal Access Token (should not be needed normally)

### 5. Enable Actions
Enable GitHub Actions in your fork. The first run takes ~1 hour to populate all data. Subsequent runs are much faster (2-10 minutes).

### 6. Manual Trigger (if needed)
If Actions don't start automatically, manually trigger the workflow.

## 🛠️ Local Development

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL
- Redis

### Setup
```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Install pre-commit hooks
uvx lefthook install

# Start local services (optional)
docker-compose up -d
```

### Available Commands
```bash
# Run full pipeline
uv run generator

# Individual phases
uv run generator download    # Download data
uv run generator process     # Process into database
uv run generator ingest      # Sync to Redis

# Utilities
uv run generator status      # Show statistics
uv run generator prune cache # Clean cache files

# Quality checks
uvx ty check                 # Type checking
uvx ruff check --fix         # Linting
uvx ruff format             # Formatting
```

### More usage examples and other commands in [USAGE.md](USAGE.md)

### Go API Development
```bash
cd api
go run index.go
```

## 🏛️ Data Pipeline Details

### Data Sources
- [nattadasu/animeApi](https://github.com/nattadasu/animeApi)
- [manami-project/anime-offline-database](https://github.com/manami-project/anime-offline-database)
- [kawaiioverflow/arm](https://github.com/kawaiioverflow/arm)
- [ryuuganime/aniTrakt-IndexParser](https://github.com/ryuuganime/aniTrakt-IndexParser)
- [Kaize.io](https://kaize.io) (web scraper)
- [Nautiljon](https://nautiljon.com) (web scraper)
- [Otak Otaku](https://otakotaku.com) (web scraper)

## 📄 Licensing

This project is licensed under **AGPL-3.0-only** with no exceptions (unlike the original project which had mixed licensing).

MIT license notices are preserved where required, documented in [NOTICE.md](NOTICE.md).

## 🤝 Contributing

Contributions welcome! Please:

1. Install development dependencies: `uv sync`
2. Set up pre-commit hooks: `uvx lefthook install`
3. Follow the existing code style
4. Ensure all tests pass: `uvx ty check && uvx ruff check`

## 📊 API Schema

The API returns JSON objects conforming to this TypeScript interface:

```typescript
interface AnimeData {
  title: string;
  anidb: number | null;
  anilist: number | null;
  animenewsnetwork: number | null;
  animeplanet: string | null;
  anisearch: number | null;
  annict: number | null;
  imdb: string | null;  // tt1234567 format
  kaize: string | null;
  kaize_id: number | null;
  kitsu: number | null;
  livechart: number | null;
  myanimelist: number | null;
  nautiljon: string | null;
  nautiljon_id: number | null;
  notify: string | null;  // Base64 encoded
  otakotaku: number | null;
  shikimori: number | null;
  shoboi: number | null;
  silveryasha: number | null;
  simkl: number | null;
  themoviedb: number | null;
  trakt: number | null;
  trakt_type: "shows" | "movies" | null;
  trakt_season: number | null;
}
```

## 🎯 Provider-Specific Notes

### Kitsu
Use numeric IDs only. Convert slugs via Kitsu API:
```http
GET https://kitsu.app/api/edge/anime?filter[slug]=cowboy-bebop
```

### Trakt
Format: `/trakt/shows/{id}` or `/trakt/movies/{id}`  
Season-specific: `/trakt/shows/{id}/seasons/{season}`

### TMDB
Format: `/themoviedb/movie/{id}` (movies only)

### Shikimori
Uses MyAnimeList IDs. Remove alphabetical prefixes (e.g., `z218` → `218`)

## 🙏 Acknowledgments

Built upon the excellent work of:
- [nattadasu](https://github.com/nattadasu) - Original AnimeAPI
- [manami-project](https://github.com/manami-project) - anime-offline-database
- [kawaiioverflow](https://github.com/kawaiioverflow) - ARM project

Special thanks to all the anime database maintainers and the anime community for making this data freely available.

---

**🔗 Live API**: [https://ids.moe](https://ids.moe)  
**📚 Original Project**: [nattadasu/animeApi](https://github.com/nattadasu/animeapi)  
**🐛 Issues**: [Report here](https://github.com/tajoumaru/ids.moe/issues)

# ids.moe - High-Performance Anime ID Mapping API

A blazingly fast RESTful API that provides anime relation mapping across multiple anime databases. Complete rewrite of the original [nattadasu/animeApi](https://github.com/nattadasu/animeapi) with significant performance improvements and modern infrastructure.

This project is forked from [nattadasu/animeApi](https://github.com/nattadasu/animeapi) and transformed with a completely rewritten data pipeline and API architecture optimized for speed and scalability.

## 🚀 Key Improvements

- **Over 100x Faster API Response**: TypeScript-based API with Cloudflare Workers KV
  - Average response time of **~0.003s** (down from ~0.400s on `animeapi.my.id`)
- **Much Faster Data Processing**: PostgreSQL with `COPY FROM` insertions and multiprocessing
- **Intelligent Caching**: Only downloads & processes changed data with hash-based detection
- **Space Efficient**: Two-tier KV structure (300k ID mappings → internal IDs → full objects)
- **Serverless Ready & Free**: Meant to deploy with Cloudflare Workers & Neon Free Tiers out of the box
- **Modern Pipeline**: GitHub Actions with dependency caching and incremental updates

## 🏗️ Architecture

### API Layer (TypeScript)
- **Runtime**: TypeScript with Wrangler/Cloudflare Workers
- **Hosting**: Cloudflare Workers (Edge Computing)
- **Response Time**: ~0.003s typical response
  - Globally distributed with edge locations worldwide
  - Automatic regional routing for optimal latency

### Data Pipeline (Python)
- **Database**: PostgreSQL on Neon (remote or local)
- **Cache**: Cloudflare Workers KV (edge-replicated key-value store)
- **Processing**: Many operations multithreaded and optimized
- **Scheduling**: GitHub Actions (nightly updates to the db and KV store)

### Storage Strategy
1. **Platform ID → Internal ID**: ~300k KV entries (e.g., `anilist_156` → `466`)
2. **Internal ID → Full Data**: Single KV entry per anime with all platform IDs
   - Two tiered approach is both fast and space efficient with no duplicate data
3. **Change Detection**: SHA-256 hashes stored in PostgreSQL for incremental updates

## 📊 Supported Platforms

|           Platform |  2K   | Aliases                                                                                         |
| -----------------: | :---: | :---------------------------------------------------------------------------------------------- |
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

`{"status":"OK","code":200,"request_time":"0.003s","response_time":"0.003s","request_epoch":1752908838}`

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

### 1. Deploy to Cloudflare Workers

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/tajoumaru/ids.moe)

Click the button above to:
- Clone the repo
- Set up Cloudflare Workers for the API
- Create KV namespace for caching
- Deploy the TypeScript API

**Make sure to choose a github account for the repo location. Gitlab did not work in my testing.**

After deployment, note these down:
- KV namespace ID [Find it here](https://dash.cloudflare.com/?to=/:account/workers/kv/namespaces)
- Cloudflare Account ID [Here in the right sidebar](https://dash.cloudflare.com/?to=/:account/workers-and-pages)
- Cloudflare Auth Token [Create one here with template "Edit Cloudflare Workers"](https://dash.cloudflare.com/profile/api-tokens)

### 2. Set up PostgreSQL Database
1. Go to [Neon](https://neon.tech) and create a free account
2. Create a new project (Use region us-east. Do not use your own location.)
3. Save the connection string for later

### 3. Configure GitHub Secrets
1. Go to the repo that cloudflare created on your personal github account.
2. Go to Settings -> Secrets and variables -> Actions
3. Add these as repository secrets:

**Required**:
- `DATABASE_URL` (Neon)
- `CLOUDFLARE_AUTH_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_KV_NAMESPACE_ID`

**Optional but recommended**:
Otherwise kaize id's will be skipped. Simply create an account on Kaize and enter your details here.
- `KAIZE_EMAIL`
- `KAIZE_PASSWORD`

### 4. Enable GitHub Actions
1. Go to the Actions tab in your cloned repository
2. Enable workflows
3. Manually trigger the "Run generator pipeline" workflow for initial data population

The first run takes ~1 hour to populate all data. Subsequent runs are much faster (2-10 minutes) and run automatically every night.

### 5. Verify Deployment
Once the GitHub Action completes, test your API:
(Find the url below in your cloudflare worker settings)
```bash
curl https://your-worker.workers.dev/mal/1
```

## 🛠️ Local Development

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+
- PostgreSQL
- Docker (optional, for local database)

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
docker compose up -d
```

### Available Commands
```bash
# Run full pipeline
uv run generator

# Individual phases
uv run generator download    # Download data
uv run generator process     # Process into database
uv run generator ingest      # Sync to Cloudflare KV

# Utilities
uv run generator status      # Show statistics
uv run generator prune cache # Clean cache files

# Quality checks
uvx ty check                 # Type checking
uvx ruff check --fix         # Linting
uvx ruff format             # Formatting
```

### More usage examples and other commands in [USAGE.md](USAGE.md)

### TypeScript API Development
```bash
cd api-ts
npm install
npm run dev   # Local development with Wrangler
```

### Deploy API to Cloudflare
```bash
cd api-ts
npm run deploy
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

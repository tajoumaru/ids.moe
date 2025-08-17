// Platform configuration and metadata

export interface PlatformMetadata {
  /** Canonical platform identifier */
  id: string;
  /** Display name for UI */
  displayName: string;
  /** Platform website URL */
  baseUrl: string;
  /** URL pattern for direct links to anime pages */
  urlPattern: string;
  /** Platform aliases and alternative names */
  aliases: string[];
}

// Platform synonyms mapping (from API config.ts)
export const PLATFORM_SYNONYMS = {
  anidb: ["ad", "adb", "anidb.net"],
  anilist: ["al", "anilist.co"],
  animenewsnetwork: ["an", "ann", "animenewsnetwork.com"],
  animeplanet: ["ap", "anime-planet", "anime-planet.com", "animeplanet.com"],
  anisearch: ["as", "anisearch.de", "anisearch.es", "anisearch.fr", "anisearch.it", "anisearch.jp", "anisearch.com"],
  annict: ["ac", "act", "anc", "annict.com", "annict.jp", "en.annict.com"],
  imdb: ["im", "imdb.com"],
  kaize: ["kz", "kaize.io"],
  kitsu: ["kt", "kts", "kitsu.app", "kitsu.io"],
  kurozora: ["kr", "krz", "kurozora.app"],
  letterboxd: ["lb", "letterboxd.com"],
  livechart: ["lc", "livechart.me"],
  myanili: ["my", "myani.li"],
  myanimelist: ["ma", "mal", "myanimelist.net"],
  nautiljon: ["nj", "ntj", "nautiljon.com"],
  notify: ["nf", "ntf", "ntm", "notifymoe", "notify.moe"],
  otakotaku: ["oo", "otakotaku.com"],
  shikimori: ["sh", "shk", "shiki", "shikimori.me", "shikimori.one", "shikimori.org"],
  shoboi: ["sb", "shb", "syb", "syoboi", "shobocal", "syobocal", "cal.syoboi.jp"],
  silveryasha: ["sy", "dbti", "db.silveryasha.id", "db.silveryasha.web.id"],
  simkl: ["sm", "smk", "simkl.com", "animecountdown", "animecountdown.com"],
  themoviedb: ["tm", "tmdb", "tmdb.org"],
  trakt: ["tr", "trk", "trakt.tv"],
} as const satisfies Record<string, string[]>;

// Platform metadata with display information
export const PLATFORM_METADATA: Record<string, PlatformMetadata> = {
  anidb: {
    id: "anidb",
    displayName: "AniDB",
    baseUrl: "https://anidb.net",
    urlPattern: "https://anidb.net/anime/",
    aliases: PLATFORM_SYNONYMS.anidb,
  },
  anilist: {
    id: "anilist",
    displayName: "AniList",
    baseUrl: "https://anilist.co",
    urlPattern: "https://anilist.co/anime/",
    aliases: PLATFORM_SYNONYMS.anilist,
  },
  animenewsnetwork: {
    id: "animenewsnetwork",
    displayName: "Anime News Network",
    baseUrl: "https://animenewsnetwork.com",
    urlPattern: "https://animenewsnetwork/encyclopedia/anime?id=",
    aliases: PLATFORM_SYNONYMS.animenewsnetwork,
  },
  animeplanet: {
    id: "animeplanet",
    displayName: "Anime-Planet",
    baseUrl: "https://www.anime-planet.com",
    urlPattern: "https://www.anime-planet.com/anime/",
    aliases: PLATFORM_SYNONYMS.animeplanet,
  },
  anisearch: {
    id: "anisearch",
    displayName: "AniSearch",
    baseUrl: "https://www.anisearch.com",
    urlPattern: "https://www.anisearch.com/anime/",
    aliases: PLATFORM_SYNONYMS.anisearch,
  },
  annict: {
    id: "annict",
    displayName: "Annict",
    baseUrl: "https://annict.com",
    urlPattern: "https://annict.com/works/",
    aliases: PLATFORM_SYNONYMS.annict,
  },
  imdb: {
    id: "imdb",
    displayName: "IMDb",
    baseUrl: "https://www.imdb.com",
    urlPattern: "https://www.imdb.com/title/",
    aliases: PLATFORM_SYNONYMS.imdb,
  },
  kaize: {
    id: "kaize",
    displayName: "Kaize",
    baseUrl: "https://kaize.io",
    urlPattern: "https://kaize.io/anime/",
    aliases: PLATFORM_SYNONYMS.kaize,
  },
  kitsu: {
    id: "kitsu",
    displayName: "Kitsu",
    baseUrl: "https://kitsu.app",
    urlPattern: "https://kitsu.app/anime/",
    aliases: PLATFORM_SYNONYMS.kitsu,
  },
  kurozora: {
    id: "kurozora",
    displayName: "Kurozora",
    baseUrl: "https://kurozora.app",
    urlPattern: "https://kurozora.app/myanimelist.net/anime/",
    aliases: PLATFORM_SYNONYMS.kurozora,
  },
  letterboxd: {
    id: "letterboxd",
    displayName: "Letterboxd",
    baseUrl: "https://letterboxd.com",
    urlPattern: "https://letterboxd.com/tmdb/",
    aliases: PLATFORM_SYNONYMS.letterboxd,
  },
  livechart: {
    id: "livechart",
    displayName: "LiveChart",
    baseUrl: "https://www.livechart.me",
    urlPattern: "https://www.livechart.me/anime/",
    aliases: PLATFORM_SYNONYMS.livechart,
  },
  myanili: {
    id: "myanili",
    displayName: "MyAniLi",
    baseUrl: "https://myani.li",
    urlPattern: "https://myani.li/#/anime/details/",
    aliases: PLATFORM_SYNONYMS.myanili,
  },
  myanimelist: {
    id: "myanimelist",
    displayName: "MyAnimeList",
    baseUrl: "https://myanimelist.net",
    urlPattern: "https://myanimelist.net/anime/",
    aliases: PLATFORM_SYNONYMS.myanimelist,
  },
  nautiljon: {
    id: "nautiljon",
    displayName: "Nautiljon",
    baseUrl: "https://www.nautiljon.com",
    urlPattern: "https://www.nautiljon.com/animes/",
    aliases: PLATFORM_SYNONYMS.nautiljon,
  },
  notify: {
    id: "notify",
    displayName: "Notify.moe",
    baseUrl: "https://notify.moe",
    urlPattern: "https://notify.moe/anime/",
    aliases: PLATFORM_SYNONYMS.notify,
  },
  otakotaku: {
    id: "otakotaku",
    displayName: "Otakotaku",
    baseUrl: "https://otakotaku.com",
    urlPattern: "https://otakotaku.com/anime/view/",
    aliases: PLATFORM_SYNONYMS.otakotaku,
  },
  shikimori: {
    id: "shikimori",
    displayName: "Shikimori",
    baseUrl: "https://shikimori.one",
    urlPattern: "https://shikimori.one/animes/",
    aliases: PLATFORM_SYNONYMS.shikimori,
  },
  shoboi: {
    id: "shoboi",
    displayName: "Shoboi",
    baseUrl: "http://cal.syoboi.jp",
    urlPattern: "https://cal.syoboi.jp/tid/",
    aliases: PLATFORM_SYNONYMS.shoboi,
  },
  silveryasha: {
    id: "silveryasha",
    displayName: "Silver Yasha",
    baseUrl: "https://db.silveryasha.id",
    urlPattern: "https://db.silveryasha.id/anime/",
    aliases: PLATFORM_SYNONYMS.silveryasha,
  },
  simkl: {
    id: "simkl",
    displayName: "Simkl",
    baseUrl: "https://simkl.com",
    urlPattern: "https://simkl.com/anime/",
    aliases: PLATFORM_SYNONYMS.simkl,
  },
  themoviedb: {
    id: "themoviedb",
    displayName: "TMDB",
    baseUrl: "https://www.themoviedb.org",
    urlPattern: "https://www.themoviedb.org/movie/",
    aliases: PLATFORM_SYNONYMS.themoviedb,
  },
  trakt: {
    id: "trakt",
    displayName: "Trakt",
    baseUrl: "https://trakt.tv",
    urlPattern: "https://trakt.tv/",
    aliases: PLATFORM_SYNONYMS.trakt,
  },
} as const;

// Build platform lookup map for fast resolution (from API utils.ts)
export const PLATFORM_LOOKUP: Record<string, string> = {};
for (const [platform, aliases] of Object.entries(PLATFORM_SYNONYMS)) {
  PLATFORM_LOOKUP[platform] = platform;
  for (const alias of aliases) {
    PLATFORM_LOOKUP[alias] = platform;
  }
}

// Valid targets for redirect (from API config.ts)
export const VALID_TARGETS = new Set(Object.keys(PLATFORM_SYNONYMS));

// Route paths for building URIs (from API config.ts)
export const ROUTE_PATHS: Record<string, string> = Object.fromEntries(
  Object.entries(PLATFORM_METADATA).map(([key, meta]) => [key, meta.urlPattern])
);

/**
 * Get all platform display names for UI
 */
export function getPlatformDisplayNames(): string[] {
  return Object.values(PLATFORM_METADATA).map(meta => meta.displayName);
}

/**
 * Get platform metadata by ID
 */
export function getPlatformMetadata(platformId: string): PlatformMetadata | undefined {
  return PLATFORM_METADATA[platformId];
}

/**
 * Resolve platform aliases to canonical platform names
 */
export function resolvePlatform(platform: string): string {
  const normalized = platform.toLowerCase();
  return PLATFORM_LOOKUP[normalized] || platform;
}

/**
 * Check if a platform is a valid redirect target
 */
export function isValidTarget(target: string): boolean {
  const resolved = resolvePlatform(target);
  return VALID_TARGETS.has(resolved);
}

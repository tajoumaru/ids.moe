// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

// Platform synonyms mapping
export const PLATFORM_SYNONYMS: Record<string, string[]> = {
  anidb: ['ad', 'adb', 'anidb.net'],
  anilist: ['al', 'anilist.co'],
  animenewsnetwork: ['an', 'ann', 'animenewsnetwork.com'],
  animeplanet: ['ap', 'anime-planet', 'anime-planet.com', 'animeplanet.com'],
  anisearch: ['as', 'anisearch.de', 'anisearch.es', 'anisearch.fr', 'anisearch.it', 'anisearch.jp', 'anisearch.com'],
  annict: ['ac', 'act', 'anc', 'annict.com', 'annict.jp', 'en.annict.com'],
  imdb: ['im', 'imdb.com'],
  kaize: ['kz', 'kaize.io'],
  kitsu: ['kt', 'kts', 'kitsu.app', 'kitsu.io'],
  kurozora: ['kr', 'krz', 'kurozora.app'],
  letterboxd: ['lb', 'letterboxd.com'],
  livechart: ['lc', 'livechart.me'],
  myanili: ['my', 'myani.li'],
  myanimelist: ['ma', 'mal', 'myanimelist.net'],
  nautiljon: ['nj', 'ntj', 'nautiljon.com'],
  notify: ['nf', 'ntf', 'ntm', 'notifymoe', 'notify.moe'],
  otakotaku: ['oo', 'otakotaku.com'],
  shikimori: ['sh', 'shk', 'shiki', 'shikimori.me', 'shikimori.one', 'shikimori.org'],
  shoboi: ['sb', 'shb', 'syb', 'syoboi', 'shobocal', 'syobocal', 'cal.syoboi.jp'],
  silveryasha: ['sy', 'dbti', 'db.silveryasha.id', 'db.silveryasha.web.id'],
  simkl: ['sm', 'smk', 'simkl.com', 'animecountdown', 'animecountdown.com'],
  themoviedb: ['tm', 'tmdb', 'tmdb.org'],
  trakt: ['tr', 'trk', 'trakt.tv'],
};

// Route paths for building URIs
export const ROUTE_PATHS: Record<string, string> = {
  anidb: 'https://anidb.net/anime/',
  anilist: 'https://anilist.co/anime/',
  animenewsnetwork: 'https://animenewsnetwork/encyclopedia/anime?id=',
  animeplanet: 'https://www.anime-planet.com/anime/',
  anisearch: 'https://www.anisearch.com/anime/',
  annict: 'https://annict.com/works/',
  imdb: 'https://www.imdb.com/title/',
  kaize: 'https://kaize.io/anime/',
  kitsu: 'https://kitsu.app/anime/',
  kurozora: 'https://kurozora.app/myanimelist.net/anime/',
  letterboxd: 'https://letterboxd.com/tmdb/',
  livechart: 'https://www.livechart.me/anime/',
  myanili: 'https://myani.li/#/anime/details/',
  myanimelist: 'https://myanimelist.net/anime/',
  nautiljon: 'https://www.nautiljon.com/animes/',
  notify: 'https://notify.moe/anime/',
  otakotaku: 'https://otakotaku.com/anime/view/',
  shikimori: 'https://shikimori.one/animes/',
  shoboi: 'https://cal.syoboi.jp/tid/',
  silveryasha: 'https://db.silveryasha.id/anime/',
  simkl: 'https://simkl.com/anime/',
  themoviedb: 'https://www.themoviedb.org/movie/',
  trakt: 'https://trakt.tv/',
};

// Build platform lookup map for fast resolution
export const PLATFORM_LOOKUP: Record<string, string> = {};
for (const [platform, aliases] of Object.entries(PLATFORM_SYNONYMS)) {
  PLATFORM_LOOKUP[platform] = platform;
  for (const alias of aliases) {
    PLATFORM_LOOKUP[alias] = platform;
  }
}

// Valid targets for redirect
export const VALID_TARGETS = new Set(Object.keys(PLATFORM_SYNONYMS));
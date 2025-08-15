// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

export interface Env {
  IDS_KV: KVNamespace;
  ASSETS: Fetcher;
  ANALYTICS: AnalyticsEngineDataset;
  AUTH_CACHE: KVNamespace;
  RATE_LIMIT: KVNamespace;
  CLERK_SECRET_KEY?: string;
  CLERK_ISSUER?: string;
  CLERK_AUTHORIZED_PARTIES?: string;
  REQUIRE_AUTH?: string; // "true" to enable authentication
}

export interface ErrorResponse {
  error: string;
  code: number;
  message: string;
}

export interface StatusResponse {
  status: string;
  code: number;
  request_time: string;
  response_time: string;
  request_epoch: number;
}

export interface AnimeData {
  title: string;
  anidb: number | null;
  anilist: number | null;
  animenewsnetwork: number | null;
  animeplanet: string | null;
  anisearch: number | null;
  annict: number | null;
  imdb: string | null;
  kaize: string | null;
  kaize_id: number | null;
  kitsu: number | null;
  livechart: number | null;
  myanimelist: number | null;
  nautiljon: string | null;
  nautiljon_id: number | null;
  notify: string | null;
  otakotaku: number | null;
  shikimori: number | null;
  shoboi: number | null;
  silveryasha: number | null;
  simkl: number | null;
  themoviedb: number | null;
  themoviedb_season?: number | null;
  themoviedb_type?: 'movie' | 'tv' | null;
  trakt: number | null;
  trakt_season?: number | null;
  trakt_type?: 'movies' | 'shows' | null;
}

export type Platform = keyof Omit<AnimeData, 'title' | 'themoviedb_season' | 'themoviedb_type' | 'trakt_season' | 'trakt_type'>;

export interface AuthUser {
  userId: string;
  email?: string;
  tier?: 'free' | 'pro' | 'enterprise';
  rateLimit?: number;
}

export interface RouteContext {
  request: Request;
  env: Env;
  ctx: ExecutionContext;
  user?: AuthUser; // Authenticated user info
}

export interface QueryParams {
  [key: string]: string | undefined;
}

export interface RateLimitInfo {
  remaining: number;
  reset: number;
  limit: number;
}

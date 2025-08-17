// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import type { components, paths } from "./schema";

export interface Env {
    IDS_KV: KVNamespace;
    ASSETS: Fetcher;
    ANALYTICS: AnalyticsEngineDataset;
    AUTH_CACHE: KVNamespace;
    RATE_LIMIT: KVNamespace;
    DATA_CACHE: KVNamespace;
    CLERK_SECRET_KEY?: string;
    CLERK_ISSUER?: string;
    CLERK_AUTHORIZED_PARTIES?: string;
    REQUIRE_AUTH?: string; // "true" to enable authentication
}

// Use generated schema types instead of duplicating them
export type AnimeData = components["schemas"]["Anime"];
export type ErrorResponse = components["schemas"]["Error"];

// The Status schema from OpenAPI doesn't match our internal needs, keep custom type
export interface StatusResponse {
    status: string;
    code: number;
    request_time: string;
    response_time: string;
    request_epoch: number;
}

// Use Heartbeat schema for the heartbeat endpoint
export type HeartbeatResponse = components["schemas"]["Heartbeat"];
export type StatusSchema = components["schemas"]["Status"];

// Export path types for type-safe route handling
export type ApiPaths = paths;
export type PlatformPathParams = paths["/{platform}/{id}"]["get"]["parameters"]["path"];
export type RedirectQueryParams = paths["/redirect"]["get"]["parameters"]["query"];

export type Platform = keyof Omit<
    AnimeData,
    "title" | "themoviedb_season" | "themoviedb_type" | "trakt_season" | "trakt_type"
>;

export interface AuthUser {
    userId: string;
    email?: string;
    tier?: "free" | "pro" | "enterprise";
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

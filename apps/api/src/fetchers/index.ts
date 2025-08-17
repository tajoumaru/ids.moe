// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import type { Env } from "../types";
import { AniDBFetcher } from "./anidb";
import { AniListFetcher } from "./anilist";
import { SourceRegistry } from "./base";
import { DataCache } from "./cache";
import { KitsuFetcher } from "./kitsu";
import { MyAnimeListFetcher } from "./myanimelist";

// Create fetcher with cache
export function getFetcher(sourceName: string, env: Env) {
    const cache = env.DATA_CACHE ? new DataCache(env.DATA_CACHE) : undefined;

    switch (sourceName) {
        case "anidb":
            return new AniDBFetcher(cache);
        case "anilist":
            return new AniListFetcher(cache);
        case "kitsu":
            return new KitsuFetcher(cache);
        case "myanimelist":
            return new MyAnimeListFetcher(cache);
        default:
            return undefined;
    }
}

// Register all available fetchers (fallback without cache)
SourceRegistry.register(new AniDBFetcher());
SourceRegistry.register(new AniListFetcher());
SourceRegistry.register(new KitsuFetcher());
SourceRegistry.register(new MyAnimeListFetcher());

// Re-export for convenience
export type { CacheOptions, SourceFetcher } from "./base";
export { CachedSourceFetcher, SourceRegistry } from "./base";
export { DataCache } from "./cache";

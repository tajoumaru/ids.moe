// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import type { CacheOptions, DataCache } from "./cache";

export type { CacheOptions } from "./cache";

export type AnimeData = {
    title: {
        english: string | null;
        native: string | null;
        romaji: string | null;
    };
    description: string | null;
    genres: string[] | null;
    season: string | null;
    seasonYear: number | null;
    format: string | null;
    episodes: number | null;
    averageScore: number | null;
    coverImage: string | null;
};

type ErrorMessage = {
    error: string;
};

/**
 * Base interface for all source fetchers
 */
export interface SourceFetcher {
    readonly sourceName: string;
    fetchData(id: number | string): Promise<AnimeData | ErrorMessage>;
}

/**
 * Base class for cached source fetchers
 */
export abstract class CachedSourceFetcher implements SourceFetcher {
    abstract readonly sourceName: string;
    protected cache?: DataCache;
    protected cacheOptions?: CacheOptions;

    constructor(cache?: DataCache, cacheOptions?: CacheOptions) {
        this.cache = cache;
        this.cacheOptions = cacheOptions;
    }

    async fetchData(id: number | string): Promise<AnimeData | ErrorMessage> {
        const cacheKey = String(id);

        // Try to get from cache first
        if (this.cache) {
            try {
                const cached = await this.cache.get(this.sourceName, cacheKey, this.cacheOptions);
                if (cached) {
                    console.log("Cache hit");
                    return cached;
                }
            } catch (error) {
                console.error(`Cache read error for ${this.sourceName}:${cacheKey}:`, error);
            }
        }

        // Fetch from source
        console.log("Cache miss");
        const result = await this.fetchFromSource(id);

        // Cache successful results (fire-and-forget)
        if (this.cache && result && !("error" in result)) {
            this.cache.set(this.sourceName, cacheKey, result, this.cacheOptions).catch((error) => {
                console.error(`Cache write error for ${this.sourceName}:${cacheKey}:`, error);
            });
        }

        return result;
    }

    protected abstract fetchFromSource(id: number | string): Promise<AnimeData | ErrorMessage>;
}

/**
 * Registry for managing source fetchers
 */
const sources = new Map<string, SourceFetcher>();

export const SourceRegistry = {
    register(fetcher: SourceFetcher): void {
        sources.set(fetcher.sourceName, fetcher);
    },

    get(sourceName: string): SourceFetcher | undefined {
        return sources.get(sourceName);
    },

    getSupportedSources(): string[] {
        return Array.from(sources.keys());
    },
};

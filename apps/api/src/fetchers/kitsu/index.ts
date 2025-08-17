// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { CachedSourceFetcher } from "../base";
import type { KitsuResponse } from "./types";

/**
 * Kitsu API fetcher implementation
 */
export class KitsuFetcher extends CachedSourceFetcher {
    readonly sourceName = "kitsu";
    private readonly apiUrl = "https://kitsu.app/api/edge/anime";

    protected async fetchFromSource(id: number | string) {
        const animeId = String(id);

        try {
            const response = await fetch(`${this.apiUrl}?filter[id]=${animeId}`, {
                method: "GET",
                headers: {
                    Accept: "application/vnd.api+json",
                    "Content-Type": "application/vnd.api+json",
                },
            });

            if (!response.ok) {
                throw new Error(`Kitsu API error: ${response.status} ${response.statusText}`);
            }

            const data = (await response.json()) as KitsuResponse;

            if (!data.data || data.data.length === 0) {
                console.error(`No media found with ID ${animeId} at ${this.sourceName}`);
                return { error: `No media found with ID ${animeId} at ${this.sourceName}` };
            }

            const anime = data.data[0];
            const attrs = anime.attributes;

            // Extract year from startDate if available
            let seasonYear: number | null = null;
            if (attrs.startDate) {
                const year = new Date(attrs.startDate).getFullYear();
                if (!Number.isNaN(year)) {
                    seasonYear = year;
                }
            }

            // Convert averageRating to number
            let averageScore: number | null = null;
            if (attrs.averageRating) {
                const score = parseFloat(attrs.averageRating);
                if (!Number.isNaN(score)) {
                    averageScore = Math.round(score);
                }
            }

            return {
                title: {
                    english: attrs.titles?.en || null,
                    native: attrs.titles?.ja_jp || null,
                    romaji: attrs.titles?.en_jp || attrs.canonicalTitle || null,
                },
                description: attrs.description || attrs.synopsis || null,
                genres: null, // Kitsu requires additional API calls for genres
                season: null, // Would need to derive from startDate
                seasonYear: seasonYear,
                format: attrs.subtype || null,
                episodes: attrs.episodeCount || null,
                averageScore: averageScore,
                coverImage: attrs.posterImage?.original || null,
            };
        } catch (error) {
            console.error(`Failed to fetch Kitsu data for ID ${animeId}:`, error);
            throw error;
        }
    }
}

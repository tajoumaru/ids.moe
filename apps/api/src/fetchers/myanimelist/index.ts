// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { CachedSourceFetcher } from "../base";
import type { JikanErrorResponse, JikanResponse } from "./types";

/**
 * MyAnimeList API fetcher implementation using Jikan.moe v4 API
 */
export class MyAnimeListFetcher extends CachedSourceFetcher {
    readonly sourceName = "myanimelist";
    private readonly apiUrl = "https://api.jikan.moe/v4";

    protected async fetchFromSource(id: number | string) {
        const malId = Number(id);

        if (Number.isNaN(malId)) {
            throw new Error(`Invalid MyAnimeList ID: ${id}`);
        }

        try {
            const response = await fetch(`${this.apiUrl}/anime/${malId}`, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
            });

            if (!response.ok) {
                if (response.status === 404) {
                    console.error(`No anime found with ID ${malId} at ${this.sourceName}`);
                    return { error: `No anime found with ID ${malId} at ${this.sourceName}` };
                }
                throw new Error(`Jikan API error: ${response.status} ${response.statusText}`);
            }

            const data = (await response.json()) as JikanResponse | JikanErrorResponse;

            if ("error" in data) {
                console.error(`Jikan API error for ID ${malId}:`, data.message);
                return { error: `Jikan API error: ${data.message}` };
            }

            const anime = data.data;

            // Extract genre names
            const genres = anime.genres?.map((genre) => genre.name) || null;

            // Determine the best title to use for English
            let englishTitle = anime.title_english;
            if (!englishTitle && anime.titles) {
                // Try to find an English title from the titles array
                const englishTitleObj = anime.titles.find((t) => t.type === "English" || t.type === "Default");
                englishTitle = englishTitleObj?.title || null;
            }

            // Use the main title as fallback for romaji
            const romajiTitle = anime.title || null;

            return {
                title: {
                    english: englishTitle,
                    native: anime.title_japanese,
                    romaji: romajiTitle,
                },
                description: anime.synopsis,
                genres: genres,
                season: anime.season,
                seasonYear: anime.year,
                format: anime.type,
                episodes: anime.episodes,
                averageScore: anime.score ? Math.round(anime.score * 10) : null, // Convert 0-10 scale to 0-100
                coverImage: anime.images?.jpg?.large_image_url || anime.images?.jpg?.image_url || null,
            };
        } catch (error) {
            console.error(`Failed to fetch MyAnimeList data for ID ${malId}:`, error);
            throw error;
        }
    }
}

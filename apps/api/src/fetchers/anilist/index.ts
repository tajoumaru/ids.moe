// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { CachedSourceFetcher } from "../base";
import query from "./query.gql";
import type { AniListResponse } from "./types";

/**
 * AniList API fetcher implementation
 */
export class AniListFetcher extends CachedSourceFetcher {
    readonly sourceName = "anilist";
    private readonly apiUrl = "https://graphql.anilist.co";

    protected async fetchFromSource(id: number | string) {
        const mediaId = Number(id);

        if (Number.isNaN(mediaId)) {
            throw new Error(`Invalid AniList media ID: ${id}`);
        }

        const variables = {
            mediaId: mediaId,
        };

        try {
            const response = await fetch(this.apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    query,
                    variables: variables,
                }),
            });

            const data = (await response.json()) as AniListResponse;

            if (data.errors || !data.data.Media) {
                console.error(`No media found with ID ${mediaId} at ${this.sourceName}`);
                return { error: `No media found with ID ${mediaId} at ${this.sourceName}` };
            }

            if (!response.ok) {
                throw new Error(`AniList API error: ${response.status} ${response.statusText}`);
            }

            const media = data.data.Media;

            return {
                title: {
                    english: media.title.english,
                    native: media.title.native,
                    romaji: media.title.romaji,
                },
                description: media.description,
                genres: media.genres,
                season: media.season,
                seasonYear: media.seasonYear,
                format: media.format,
                episodes: media.episodes,
                averageScore: media.averageScore,
                coverImage: media.coverImage?.extraLarge ?? null,
            };
        } catch (error) {
            console.error(`Failed to fetch AniList data for ID ${mediaId}:`, error);
            throw error;
        }
    }
}

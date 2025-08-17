// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { getFetcher, SourceRegistry } from "../fetchers";
import { getAnimeData } from "../kv";
import type { AnimeData, RouteContext } from "../types";
import { createErrorResponse, createJsonResponse, resolvePlatform } from "../utils";

/**
 * Handle /data/{platform}/{id} endpoint with optional ?source parameter
 * Resolves IDs and fetches data from the specified source API
 */
export async function handleDataRoute(context: RouteContext, path: string): Promise<Response> {
    const url = new URL(context.request.url);
    const parts = path.replace(/^\/+|\/+$/g, "").split("/");

    if (parts.length !== 3 || parts[0] !== "data") {
        return createErrorResponse(
            "Invalid request",
            400,
            "Invalid data endpoint format. Expected: /data/{platform}/{id}",
        );
    }

    const inputPlatform = resolvePlatform(parts[1].toLowerCase());
    const inputId = parts[2];
    const source = url.searchParams.get("source") || "anilist";

    // Get fetcher with cache
    const fetcher = getFetcher(source, context.env);
    if (!fetcher) {
        const supportedSources = SourceRegistry.getSupportedSources();
        return createErrorResponse(
            "Invalid source",
            400,
            `Source '${source}' is not supported. Supported sources: ${supportedSources.join(", ")}`,
        );
    }

    try {
        let resolvedAnimeData: AnimeData | null = null;
        let sourceId: number | string | null = null;

        // If input platform matches source, skip resolution
        if (inputPlatform === source) {
            sourceId = inputId;
        } else {
            // Resolve the input platform/id to get all IDs
            resolvedAnimeData = await getAnimeData(context.env.IDS_KV, inputPlatform, inputId);

            if (!resolvedAnimeData) {
                return createErrorResponse("Not found", 404, `Platform ${inputPlatform} with ID ${inputId} not found`);
            }

            // Extract the source platform ID from resolved data
            sourceId = getSourceId(resolvedAnimeData, source);

            if (!sourceId) {
                return createErrorResponse("Not found", 404, `No ${source} ID found for ${inputPlatform}:${inputId}`);
            }
        }

        // Fetch data from the source API
        const sourceData = await fetcher.fetchData(sourceId);

        if ("error" in sourceData) {
            return createErrorResponse("Not Found", 404, sourceData.error);
        }

        return createJsonResponse(sourceData);
    } catch (error) {
        console.error(`Error fetching data for ${inputPlatform}:${inputId} from ${source}:`, error);
        return createErrorResponse("Internal server error", 500, "Failed to fetch data from source API");
    }
}

/**
 * Extract the ID for a specific source platform from anime data
 */
function getSourceId(animeData: AnimeData, source: string): number | string | null {
    switch (source) {
        case "anilist":
            return animeData.anilist;
        case "myanimelist":
            return animeData.myanimelist;
        case "kitsu":
            return animeData.kitsu;
        case "anidb":
            return animeData.anidb;
        // Add more platforms as needed
        default:
            return null;
    }
}

// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { XMLParser } from "fast-xml-parser";
import { CachedSourceFetcher } from "../base";
import type { AniDBAnime, AniDBTitle } from "./types";

/**
 * AniDB API fetcher implementation
 */
export class AniDBFetcher extends CachedSourceFetcher {
    readonly sourceName = "anidb";
    private readonly apiUrl = "http://api.anidb.net:9001/httpapi";
    private readonly clientName = "idsmoe";
    private readonly clientVersion = "1";
    private readonly protocolVersion = "1";

    protected async fetchFromSource(id: number | string) {
        const anidbId = Number(id);

        if (Number.isNaN(anidbId)) {
            throw new Error(`Invalid AniDB ID: ${id}`);
        }

        try {
            const url = new URL(this.apiUrl);
            url.searchParams.set("request", "anime");
            url.searchParams.set("client", this.clientName);
            url.searchParams.set("clientver", this.clientVersion);
            url.searchParams.set("protover", this.protocolVersion);
            url.searchParams.set("aid", String(anidbId));

            const response = await fetch(url.toString(), {
                method: "GET",
                headers: {
                    Accept: "application/xml",
                    "Accept-Encoding": "gzip, deflate",
                },
            });

            if (!response.ok) {
                if (response.status === 404) {
                    console.error(`No anime found with ID ${anidbId} at ${this.sourceName}`);
                    return { error: `No anime found with ID ${anidbId} at ${this.sourceName}` };
                }
                throw new Error(`AniDB API error: ${response.status} ${response.statusText}`);
            }

            // The response is automatically decompressed by the fetch API
            const xmlText = await response.text();
            const anime = this.parseXML(xmlText);

            if (!anime) {
                console.error(`Failed to parse anime data for ID ${anidbId} at ${this.sourceName}`);
                return { error: `Failed to parse anime data for ID ${anidbId} at ${this.sourceName}` };
            }

            // Extract titles by type and language
            const englishTitle =
                this.findTitle(anime.titles, "en", ["official", "main"]) ||
                this.findTitle(anime.titles, "en", ["synonym", "short"]);
            const nativeTitle =
                this.findTitle(anime.titles, "ja", ["official", "main"]) ||
                this.findTitle(anime.titles, "x-jat", ["main"]);
            const romajiTitle =
                this.findTitle(anime.titles, "x-jat", ["main", "official"]) ||
                this.findTitle(anime.titles, "en", ["short"]);

            // Parse season and year from startdate
            const { season, seasonYear } = this.parseSeasonFromDate(anime.startdate);

            // Convert rating from 0-10 to 0-100 scale
            const averageScore = anime.ratings?.permanent?.value
                ? Math.round(anime.ratings.permanent.value * 10)
                : null;

            // Construct cover image URL
            const coverImage = anime.picture ? `https://cdn-eu.anidb.net/images/main/${anime.picture}` : null;

            return {
                title: {
                    english: englishTitle,
                    native: nativeTitle,
                    romaji: romajiTitle,
                },
                description: anime.description || null,
                genres: null, // AniDB doesn't provide genres in this simple format, would need tag parsing
                season: season,
                seasonYear: seasonYear,
                format: this.mapAnimeType(anime.type),
                episodes: anime.episodecount || null,
                averageScore: averageScore,
                coverImage: coverImage,
            };
        } catch (error) {
            console.error(`Failed to fetch AniDB data for ID ${anidbId}:`, error);
            throw error;
        }
    }

    private parseXML(xmlText: string): AniDBAnime | null {
        try {
            const options = {
                ignoreAttributes: false,
                attributeNamePrefix: "@_",
                textNodeName: "#text",
                parseAttributeValue: true,
                trimValues: true,
                processEntities: true,
            };

            const parser = new XMLParser(options);
            const result = parser.parse(xmlText);

            const anime = result.anime;
            if (!anime) {
                console.error("No anime element found in parsed XML");
                return null;
            }

            const id = anime["@_id"] || "";
            const restricted = anime["@_restricted"] === "true" || anime["@_restricted"] === true;

            // Extract basic fields
            const type = anime.type || "";
            const episodecount = parseInt(anime.episodecount || "0", 10);
            const startdate = anime.startdate || "";
            const enddate = anime.enddate || "";
            const description = this.cleanDescription(anime.description || "");
            const picture = anime.picture || "";

            // Extract titles
            const titles = this.extractTitlesFromParsed(anime.titles);

            // Extract ratings
            const ratings = this.extractRatingsFromParsed(anime.ratings);

            return {
                id,
                restricted,
                type,
                episodecount,
                startdate,
                enddate,
                titles,
                description,
                ratings,
                picture: picture || undefined,
            };
        } catch (error) {
            console.error("Failed to parse AniDB XML:", error);
            return null;
        }
    }

    private cleanDescription(description: string): string {
        if (!description) return "";

        let cleaned = description;

        // Remove AniDB-specific link formatting like "http://anidb.net/ch270 [Spike Spiegel]"
        // and convert to just the display text
        cleaned = cleaned.replace(/http:\/\/anidb\.net\/[^\s]+\s+\[([^\]]+)\]/g, "$1");

        // Remove simple markup tags like [i] and [/i]
        cleaned = cleaned.replace(/\[\/?(i|b|u)\]/g, "");

        return cleaned.trim();
    }

    private extractTitlesFromParsed(titlesData: any): AniDBTitle[] {
        const titles: AniDBTitle[] = [];
        if (!titlesData?.title) return titles;

        const titleArray = Array.isArray(titlesData.title) ? titlesData.title : [titlesData.title];

        for (const titleObj of titleArray) {
            if (titleObj) {
                const lang = titleObj["@_xml:lang"] || titleObj["@_lang"] || "";
                const type = titleObj["@_type"] || "";
                const value = titleObj["#text"] || titleObj;

                if (typeof value === "string") {
                    titles.push({
                        value: value.trim(),
                        lang: lang,
                        type: type as AniDBTitle["type"],
                    });
                }
            }
        }

        return titles;
    }

    private extractRatingsFromParsed(ratingsData: any): AniDBAnime["ratings"] | undefined {
        if (!ratingsData?.permanent) return undefined;

        const permanent = ratingsData.permanent;
        const count = permanent["@_count"];
        const value = permanent["#text"] || permanent;

        if (count && value) {
            return {
                permanent: {
                    count: parseInt(count, 10),
                    value: parseFloat(value),
                },
            };
        }

        return undefined;
    }

    private findTitle(titles: AniDBTitle[], lang: string, types: string[]): string | null {
        for (const type of types) {
            const title = titles.find((t) => t.lang === lang && t.type === type);
            if (title) return title.value;
        }
        return null;
    }

    private parseSeasonFromDate(dateStr: string): { season: string | null; seasonYear: number | null } {
        if (!dateStr) return { season: null, seasonYear: null };

        const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (!match) return { season: null, seasonYear: null };

        const year = parseInt(match[1], 10);
        const month = parseInt(match[2], 10);

        let season: string;
        if (month >= 3 && month <= 5) {
            season = "SPRING";
        } else if (month >= 6 && month <= 8) {
            season = "SUMMER";
        } else if (month >= 9 && month <= 11) {
            season = "FALL";
        } else {
            season = "WINTER";
        }

        return { season, seasonYear: year };
    }

    private mapAnimeType(type: string): string | null {
        const typeMap: Record<string, string> = {
            "TV Series": "TV",
            Movie: "MOVIE",
            OVA: "OVA",
            ONA: "ONA",
            Special: "SPECIAL",
            "Music Video": "MUSIC",
        };

        return typeMap[type] || type || null;
    }
}

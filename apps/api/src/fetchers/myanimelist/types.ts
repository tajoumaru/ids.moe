interface JikanTitle {
    type: string;
    title: string;
}

interface JikanAiredDate {
    day: number;
    month: number;
    year: number;
}

interface JikanAired {
    from: string;
    to: string;
    prop: {
        from: JikanAiredDate;
        to: JikanAiredDate;
        string: string;
    };
}

interface JikanAnimeData {
    mal_id: number;
    url: string;
    title: string;
    title_english: string | null;
    title_japanese: string | null;
    title_synonyms: string[];
    titles: JikanTitle[];
    type: "TV" | "OVA" | "Movie" | "Special" | "ONA" | "Music";
    source: string;
    episodes: number | null;
    status: "Finished Airing" | "Currently Airing" | "Not yet aired";
    airing: boolean;
    aired: JikanAired;
    duration: string;
    rating: string;
    score: number | null;
    scored_by: number;
    rank: number | null;
    popularity: number;
    synopsis: string | null;
    background: string | null;
    season: "winter" | "spring" | "summer" | "fall" | null;
    year: number | null;
    genres: Array<{
        mal_id: number;
        type: string;
        name: string;
        url: string;
    }>;
    images: {
        jpg: {
            image_url: string;
            small_image_url: string;
            large_image_url: string;
        };
        webp: {
            image_url: string;
            small_image_url: string;
            large_image_url: string;
        };
    };
}

export interface JikanResponse {
    data: JikanAnimeData;
}

export interface JikanErrorResponse {
    status: number;
    type: string;
    message: string;
    error: string;
}

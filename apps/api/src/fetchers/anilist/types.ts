interface AniListTitle {
    english: string | null;
    native: string | null;
    romaji: string | null;
}

interface AniListCoverImage {
    extraLarge: string | null;
}

interface AniListMedia {
    title: AniListTitle;
    description: string | null;
    genres: string[] | null;
    season: string | null;
    seasonYear: number | null;
    format: string | null;
    episodes: number | null;
    averageScore: number | null;
    coverImage: AniListCoverImage | null;
}

export interface AniListResponse {
    data: {
        Media: AniListMedia | null;
    };
    errors?: Array<{ message: string; status: number; locations: Array<{ line: number; column: number }> }>;
}

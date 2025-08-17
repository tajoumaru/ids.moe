interface KitsuTitles {
    en?: string;
    en_jp?: string;
    ja_jp?: string;
}

interface KitsuPosterImage {
    original?: string;
}

interface KitsuAnimeAttributes {
    canonicalTitle?: string;
    titles?: KitsuTitles;
    description?: string;
    synopsis?: string;
    startDate?: string;
    endDate?: string;
    episodeCount?: number;
    averageRating?: string;
    posterImage?: KitsuPosterImage;
    subtype?: string;
}

interface KitsuAnimeData {
    id: string;
    type: string;
    attributes: KitsuAnimeAttributes;
}

export interface KitsuResponse {
    data: KitsuAnimeData[];
    meta?: {
        count: number;
    };
}

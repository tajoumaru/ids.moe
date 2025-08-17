export interface AniDBTitle {
    value: string;
    lang: string;
    type: "main" | "official" | "synonym" | "short";
}

export interface AniDBAnime {
    id: string;
    restricted: boolean;
    type: string;
    episodecount: number;
    startdate: string;
    enddate: string;
    titles: AniDBTitle[];
    description: string;
    ratings?: {
        permanent?: {
            count: number;
            value: number;
        };
    };
    picture?: string;
}

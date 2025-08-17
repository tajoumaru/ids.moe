// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import type { AnimeData } from "./base";

export interface CacheOptions {
    ttl?: number; // Time to live in seconds
    keyPrefix?: string;
}

export interface CachedData<T = AnimeData> {
    data: T;
    timestamp: number;
    ttl: number;
}

export class DataCache {
    private kv: KVNamespace;
    private defaultTtl: number = 86400; // 24 hour default

    constructor(kv: KVNamespace, defaultTtl?: number) {
        this.kv = kv;
        if (defaultTtl) {
            this.defaultTtl = defaultTtl;
        }
    }

    private generateKey(source: string, id: string | number, prefix?: string): string {
        const baseKey = `${source}:${id}`;
        return prefix ? `${prefix}:${baseKey}` : baseKey;
    }

    async get<T = AnimeData>(source: string, id: string | number, options?: CacheOptions): Promise<T | null> {
        const key = this.generateKey(source, id, options?.keyPrefix);

        try {
            const cached = await this.kv.get<CachedData<T>>(key, "json");

            if (!cached) {
                return null;
            }

            const now = Date.now();
            const expiresAt = cached.timestamp + cached.ttl * 1000;

            if (now > expiresAt) {
                // Cache expired, delete it
                await this.kv.delete(key);
                return null;
            }

            return cached.data;
        } catch (error) {
            console.error(`Cache get error for key ${key}:`, error);
            return null;
        }
    }

    async set<T = AnimeData>(source: string, id: string | number, data: T, options?: CacheOptions): Promise<void> {
        const key = this.generateKey(source, id, options?.keyPrefix);
        const ttl = options?.ttl || this.defaultTtl;

        const cachedData: CachedData<T> = {
            data,
            timestamp: Date.now(),
            ttl,
        };

        try {
            await this.kv.put(key, JSON.stringify(cachedData), {
                expirationTtl: ttl,
            });
        } catch (error) {
            console.error(`Cache set error for key ${key}:`, error);
        }
    }

    async delete(source: string, id: string | number, options?: CacheOptions): Promise<void> {
        const key = this.generateKey(source, id, options?.keyPrefix);

        try {
            await this.kv.delete(key);
        } catch (error) {
            console.error(`Cache delete error for key ${key}:`, error);
        }
    }

    async clear(source?: string, prefix?: string): Promise<void> {
        try {
            const listOptions: KVNamespaceListOptions = {};

            if (source && prefix) {
                listOptions.prefix = `${prefix}:${source}:`;
            } else if (source) {
                listOptions.prefix = `${source}:`;
            } else if (prefix) {
                listOptions.prefix = `${prefix}:`;
            }

            const keys = await this.kv.list(listOptions);

            const deletePromises = keys.keys.map((key) => this.kv.delete(key.name));
            await Promise.all(deletePromises);
        } catch (error) {
            console.error(`Cache clear error:`, error);
        }
    }
}

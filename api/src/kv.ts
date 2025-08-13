// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { AnimeData, Env } from './types';

/**
 * Get anime data using the two-tier KV structure:
 * 1. Look up platform:id to get internal ID
 * 2. Look up internal ID to get full anime data
 */
export async function getAnimeData(
  kv: KVNamespace,
  platform: string,
  id: string
): Promise<AnimeData | null> {
  // Inline string cleaning to reduce allocations
  const platformKey = `${platform}/${decodeURIComponent(
    id.replace(/\.json$/, '').replace(/\.html$/, '').trim()
  )}`;
  
  try {
    // Step 1: Get internal ID from platform/id key
    const internalIdStr = await kv.get(platformKey);
    if (!internalIdStr) return null;
    
    // Step 2: Get anime data using internal ID
    const animeDataStr = await kv.get(internalIdStr);
    if (!animeDataStr) return null;
    
    // Direct cast to avoid intermediate parsing
    return JSON.parse(animeDataStr) as AnimeData;
  } catch {
    // Remove console.error in production for slight perf gain
    return null;
  }
}

/**
 * Check if KV is healthy by testing a known entry
 */
export async function checkKvHealth(kv: KVNamespace): Promise<boolean> {
  try {
    const testData = await getAnimeData(kv, 'myanimelist', '1');
    if (!testData) {
      return false;
    }
    
    // Verify data integrity - MAL ID 1 should have myanimelist: 1
    return testData.myanimelist === 1;
  } catch (error) {
    console.error('KV health check failed:', error);
    return false;
  }
}
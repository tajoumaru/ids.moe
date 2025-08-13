// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { RouteContext } from '../types';
import { getAnimeData } from '../kv';
import {
  createJsonResponse,
  createErrorResponse,
  createRedirectResponse,
  createTextResponse,
  resolvePlatform,
  isValidTarget,
  getGoto,
  validateTraktId
} from '../utils';

export async function handlePlatformRoute(context: RouteContext, path: string): Promise<Response> {
  const parts = path.replace(/^\/+|\/+$/g, '').split('/');

  if (parts.length === 1) {
    // Platform array route - legacy compatibility
    const platform = parts[0];

    if (path.endsWith('.tsv')) {
      return createTextResponse(
        'TSV endpoint - implement KV-based TSV generation',
        200
      );
    }

    const goto = getGoto(path, platform);
    if (isValidTarget(goto.replace('_object', '')) || platform === 'animeapi' || platform === 'aa') {
      const githubUrl = `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/${goto}.json`;
      return createRedirectResponse(githubUrl);
    }

    return createErrorResponse(
      'Invalid platform',
      400,
      `Platform ${platform} not found, please check if it is a valid platform`
    );
  }

  if (parts.length === 2) {
    // Platform lookup route
    const platform = resolvePlatform(parts[0].toLowerCase());
    const platformId = parts[1];

    try {
      const animeData = await getAnimeData(context.env.IDS_KV, platform, platformId);

      if (!animeData) {
        return createErrorResponse(
          'Not found',
          404,
          `Platform ${platform} with ID ${platformId} not found`
        );
      }

      return createJsonResponse(animeData);
    } catch (error) {
      console.error(`Error fetching anime data for ${platform}:${platformId}:`, error);
      return createErrorResponse(
        'Not found',
        404,
        `Platform ${platform} not found or not supported`
      );
    }
  }

  return createErrorResponse('Not found', 404, 'Endpoint not found');
}

export async function handleTraktRoute(context: RouteContext, path: string): Promise<Response> {
  const parts = path.replace(/^\/+|\/+$/g, '').split('/');

  if (parts.length < 3) {
    return createErrorResponse(
      'Invalid request',
      400,
      'Invalid Trakt URL format'
    );
  }

  const mediaType = parts[1];
  const mediaId = parts[2];
  let seasonId = '';

  if (parts.length > 4 && (parts[3] === 'seasons' || parts[3] === 'season') && parts.length > 4) {
    seasonId = parts[4];
  }

  if (seasonId === '0' && (mediaType === 'show' || mediaType === 'shows')) {
    return createErrorResponse(
      'Invalid season ID',
      400,
      'Season ID cannot be 0'
    );
  }

  // Ensure media type has 's' suffix
  const normalizedMediaType = mediaType.endsWith('s') ? mediaType : mediaType + 's';

  let lookupKey: string;
  if (seasonId) {
    lookupKey = `${normalizedMediaType}/${mediaId}/seasons/${seasonId}`;
  } else {
    lookupKey = `${normalizedMediaType}/${mediaId}`;
  }

  try {
    const animeData = await getAnimeData(context.env.IDS_KV, 'trakt', lookupKey);

    if (!animeData) {
      let message = `Media type ${normalizedMediaType} with ID ${mediaId}`;
      if (seasonId) {
        message += ` and season ID ${seasonId}`;
      }
      message += ' not found';

      return createErrorResponse('Not found', 404, message);
    }

    return createJsonResponse(animeData);
  } catch (error) {
    console.error(`Error fetching Trakt data for ${lookupKey}:`, error);
    return createErrorResponse('Not found', 404, 'Trakt data not found');
  }
}

export async function handleTMDBRoute(context: RouteContext, path: string): Promise<Response> {
  const parts = path.replace(/^\/+|\/+$/g, '').split('/');

  if (parts.length < 3) {
    return createErrorResponse(
      'Invalid request',
      400,
      'Invalid TMDB URL format'
    );
  }

  const mediaType = parts[1];
  const mediaId = parts[2];

  if (mediaType === 'tv' || (parts.length > 3 && parts[3] === 'season')) {
    return createErrorResponse(
      'Invalid request',
      400,
      'Currently, only `movie` are supported'
    );
  }

  const lookupKey = `movie/${mediaId}`;

  try {
    const animeData = await getAnimeData(context.env.IDS_KV, 'themoviedb', lookupKey);

    if (!animeData) {
      return createErrorResponse(
        'Not found',
        404,
        `Media type ${mediaType} with ID ${mediaId} not found`
      );
    }

    return createJsonResponse(animeData);
  } catch (error) {
    console.error(`Error fetching TMDB data for ${lookupKey}:`, error);
    return createErrorResponse('Not found', 404, 'TMDB data not found');
  }
}

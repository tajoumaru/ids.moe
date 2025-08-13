// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { RouteContext } from '../types';
import { getAnimeData } from '../kv';
import {
  createErrorResponse,
  createRedirectResponse,
  createTextResponse,
  resolvePlatform,
  isValidTarget,
  buildURI,
  buildTargetURI,
  getQueryParam,
  validateTraktId
} from '../utils';

export async function handleRedirect(context: RouteContext): Promise<Response> {
  const url = new URL(context.request.url);
  const searchParams = url.searchParams;

  // Get parameters using multiple possible parameter names
  const platform = getQueryParam(searchParams, ['platform', 'from', 'f']);
  const platformId = getQueryParam(searchParams, ['mediaid', 'id', 'i']);
  const target = getQueryParam(searchParams, ['target', 'to', 't']);
  const isRaw = getQueryParam(searchParams, ['israw', 'raw', 'r']) !== '';

  // Validate required parameters
  if (!platform) {
    return createErrorResponse(
      'Invalid platform',
      400,
      'Platform not found, please specify platform by adding `platform` parameter.'
    );
  }

  if (!platformId) {
    return createErrorResponse(
      'Invalid platform ID',
      400,
      'Platform ID not found, please specify platform ID by adding `platform_id` parameter'
    );
  }

  // Resolve platform aliases
  const resolvedPlatform = resolvePlatform(platform.toLowerCase());
  const resolvedTarget = target ? resolvePlatform(target.toLowerCase()) : '';

  // Check for unsupported source platforms
  if (['kurozora', 'myanili', 'letterboxd'].includes(resolvedPlatform)) {
    return createErrorResponse(
      'Invalid platform source',
      400,
      `Platform \`${resolvedPlatform}\` is not supported as redirect source (one-way)`
    );
  }

  // Validate target platform
  if (resolvedTarget && !isValidTarget(resolvedTarget)) {
    return createErrorResponse(
      'Invalid target',
      400,
      `Target ${resolvedTarget} not found`
    );
  }

  // Handle special platform ID transformations
  let processedId = platformId;

  if (resolvedPlatform === 'trakt') {
    const traktError = validateTraktId(platformId);
    if (traktError) {
      return createErrorResponse('Invalid Trakt ID', 400, traktError);
    }
  }

  if (resolvedPlatform === 'themoviedb' && !platformId.includes('movie')) {
    processedId = `movie/${platformId}`;
  }

  try {
    // Get anime data
    const animeData = await getAnimeData(context.env.IDS_KV, resolvedPlatform, processedId);

    if (!animeData) {
      return createErrorResponse(
        'Not found',
        404,
        `Platform ${resolvedPlatform} with ID ${platformId} not found`
      );
    }

    // If no target specified, redirect to the source platform
    if (!resolvedTarget) {
      const uri = buildURI(resolvedPlatform, processedId);
      if (!uri) {
        return createErrorResponse(
          'Invalid platform',
          400,
          `Unable to build URI for platform ${resolvedPlatform}`
        );
      }

      return generateResponse(uri, isRaw);
    }

    // Build target URI
    const targetUri = buildTargetURI(resolvedTarget, animeData);
    if (!targetUri) {
      const title = animeData.title || 'Unknown title';
      return createErrorResponse(
        'Not found',
        404,
        `${title} does not exist on ${resolvedTarget} using ${resolvedPlatform} with ID ${platformId}`
      );
    }

    return generateResponse(targetUri, isRaw);
  } catch (error) {
    console.error(`Redirect error for ${resolvedPlatform}:${processedId}:`, error);
    return createErrorResponse(
      'Not found',
      404,
      `Platform ${resolvedPlatform} with ID ${platformId} not found`
    );
  }
}

function generateResponse(uri: string, isRaw: boolean): Response {
  if (isRaw) {
    return createTextResponse(uri);
  } else {
    return createRedirectResponse(uri);
  }
}

// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { PLATFORM_LOOKUP, ROUTE_PATHS, VALID_TARGETS } from './config';
import { ErrorResponse, StatusResponse, AnimeData, QueryParams } from './types';

/**
 * Resolve platform aliases to canonical platform names
 */
export function resolvePlatform(platform: string): string {
  const normalized = platform.toLowerCase();
  return PLATFORM_LOOKUP[normalized] || platform;
}

/**
 * Check if a platform is a valid redirect target
 */
export function isValidTarget(target: string): boolean {
  const resolved = resolvePlatform(target);
  return VALID_TARGETS.has(resolved);
}

/**
 * Build URI for a platform and ID
 */
export function buildURI(platform: string, platformId: string): string {
  const basePath = ROUTE_PATHS[platform];
  if (!basePath) {
    return '';
  }
  return basePath + platformId;
}

/**
 * Build target URI for redirects
 */
export function buildTargetURI(target: string, animeData: AnimeData): string | null {
  switch (target) {
    case 'trakt':
      return buildTraktURI(animeData);
    case 'kurozora':
    case 'myanili':
      if (animeData.myanimelist !== null) {
        return ROUTE_PATHS[target] + animeData.myanimelist;
      }
      return null;
    case 'letterboxd':
      if (animeData.themoviedb !== null) {
        return ROUTE_PATHS[target] + animeData.themoviedb;
      }
      return null;
    default:
      return buildGenericURI(target, animeData);
  }
}

function buildTraktURI(animeData: AnimeData): string | null {
  if (animeData.trakt === null) {
    return null;
  }
  
  const mediaType = animeData.trakt_type || 'movies';
  const basePath = ROUTE_PATHS.trakt;
  
  if (animeData.trakt_season !== null && animeData.trakt_season !== undefined) {
    return `${basePath}${mediaType}/${animeData.trakt}/seasons/${animeData.trakt_season}`;
  }
  
  return `${basePath}${mediaType}/${animeData.trakt}`;
}

function buildGenericURI(target: string, animeData: AnimeData): string | null {
  const id = (animeData as any)[target];
  if (id === null || id === undefined) {
    return null;
  }
  
  const basePath = ROUTE_PATHS[target];
  if (!basePath) {
    return null;
  }
  
  return basePath + id;
}

/**
 * Validate Trakt ID format
 */
export function validateTraktId(platformId: string): string | null {
  const parts = platformId.split('/');
  if (parts.length > 1) {
    const id = parts[1];
    if (!/^\d+$/.test(id)) {
      const finalId = parts.slice(0, 2).join('/');
      return `Trakt ID for ${finalId} is not an \`int\`. Please convert the slug to \`int\` ID using Trakt API to proceed`;
    }
  }
  return null;
}

/**
 * Get goto parameter for legacy compatibility
 */
export function getGoto(route: string, rawPlatform: string): string {
  let goto = decodeURIComponent(route.replace(/^\/+|\/+$/g, ''));
  rawPlatform = decodeURIComponent(rawPlatform);
  
  if (goto.endsWith('.json')) {
    goto = goto.slice(0, -5);
    rawPlatform = rawPlatform.slice(0, -5);
  }
  
  const isArray = rawPlatform.endsWith('()');
  rawPlatform = rawPlatform.replace(/\(\)$/, '');
  goto = resolvePlatform(rawPlatform);
  goto = goto.replace('aa', 'animeapi');
  
  if (!isArray && !goto.includes('animeapi')) {
    goto = goto + '_object';
  }
  
  return goto;
}

/**
 * Get query parameter by multiple possible keys
 */
export function getQueryParam(params: URLSearchParams, keys: string[]): string {
  for (const key of keys) {
    const value = params.get(key);
    if (value) {
      return value;
    }
  }
  return '';
}

/**
 * Parse URL search params into QueryParams object
 */
export function parseQueryParams(searchParams: URLSearchParams): QueryParams {
  const params: QueryParams = {};
  for (const [key, value] of searchParams) {
    params[key] = value;
  }
  return params;
}

/**
 * Create JSON response
 */
export function createJsonResponse(data: any, status: number = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

/**
 * Create error response
 */
export function createErrorResponse(error: string, code: number, message: string): Response {
  const errorResponse: ErrorResponse = {
    error,
    code,
    message,
  };
  return createJsonResponse(errorResponse, code);
}

/**
 * Create redirect response
 */
export function createRedirectResponse(url: string): Response {
  return new Response(null, {
    status: 302,
    headers: {
      'Location': url,
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Create text response
 */
export function createTextResponse(text: string, status: number = 200): Response {
  return new Response(text, {
    status,
    headers: {
      'Content-Type': 'text/plain',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Create binary response for files like favicon
 */
export function createBinaryResponse(data: ArrayBuffer, contentType: string, status: number = 200): Response {
  return new Response(data, {
    status,
    headers: {
      'Content-Type': contentType,
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

/**
 * Handle CORS preflight requests
 */
export function createCorsResponse(): Response {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
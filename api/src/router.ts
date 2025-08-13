// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { RouteContext } from './types';
import { createCorsResponse, createRedirectResponse, createTextResponse, createErrorResponse } from './utils';
import { handlePlatformRoute, handleTraktRoute, handleTMDBRoute } from './handlers/platform';
import { handleStatus, handleHeartbeat, handleSchema, handleUpdated } from './handlers/status';
import { handleRedirect } from './handlers/redirect';

export async function handleRequest(context: RouteContext): Promise<Response> {
  const { request } = context;
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    return createCorsResponse();
  }

  // Only allow GET requests
  if (method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, 'Only GET requests are allowed');
  }

  const startTime = Date.now();

  try {
    // Route matching
    switch (true) {
      case path === '/':
        return createRedirectResponse('https://github.com/tajoumaru/ids.moe');

      case path === '/status':
        // Try to fetch from static assets first
        const statusAsset = await context.env.ASSETS.fetch(new Request(new URL('/status.json', request.url)));
        if (statusAsset.ok) {
          return statusAsset;
        }
        return await handleStatus();

      case path === '/heartbeat' || path === '/ping':
        return await handleHeartbeat(context, startTime);

      case path === '/schema' || path === '/schema.json':
        // Try to fetch from static assets first
        const schemaAsset = await context.env.ASSETS.fetch(new Request(new URL('/schema.json', request.url)));
        if (schemaAsset.ok) {
          return schemaAsset;
        }
        return await handleSchema();

      case path === '/updated':
        return await handleUpdated(context);

      case path === '/robots.txt':
        // Try to fetch from static assets first
        const robotsAsset = await context.env.ASSETS.fetch(request);
        if (robotsAsset.ok) {
          return robotsAsset;
        }
        return createTextResponse('User-agent: *\nDisallow:');

      case path === '/favicon.ico':
        // Fetch from static assets
        return await context.env.ASSETS.fetch(request);

      case path.startsWith('/trakt/'):
        return await handleTraktRoute(context, path);

      case path.startsWith('/themoviedb/'):
        return await handleTMDBRoute(context, path);

      case path === '/rd' || path === '/redirect':
        return await handleRedirect(context);

      default:
        // Handle platform routes
        return await handlePlatformRoute(context, path);
    }
  } catch (error) {
    console.error('Router error:', error);
    return createErrorResponse(
      'Internal server error',
      500,
      'An unexpected error occurred'
    );
  }
}
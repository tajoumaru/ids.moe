// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { Env, RouteContext } from './types';

export interface AnalyticsEvent {
  indexes?: string[];
  doubles?: number[];
  blobs?: string[];
}

export async function trackEvent(
  env: Env,
  request: Request,
  response: Response,
  startTime: number,
  user?: RouteContext['user']
): Promise<void> {
  if (!env.ANALYTICS) {
    return;
  }

  const url = new URL(request.url);
  const path = url.pathname;
  const duration = Date.now() - startTime;

  // Determine endpoint type
  let endpoint = 'unknown';
  if (path === '/') endpoint = 'root';
  else if (path === '/status') endpoint = 'status';
  else if (path === '/heartbeat' || path === '/ping') endpoint = 'heartbeat';
  else if (path === '/schema' || path === '/schema.json') endpoint = 'schema';
  else if (path === '/updated') endpoint = 'updated';
  else if (path === '/robots.txt') endpoint = 'robots';
  else if (path === '/favicon.ico') endpoint = 'favicon';
  else if (path.startsWith('/trakt/')) endpoint = 'trakt';
  else if (path.startsWith('/themoviedb/')) endpoint = 'themoviedb';
  else if (path === '/rd' || path === '/redirect') endpoint = 'redirect';
  else if (path.match(/^\/[^\/]+\/[^\/]+$/)) endpoint = 'platform_lookup';
  else endpoint = 'other';

  // Extract platform from path if it's a platform lookup
  let platform = 'none';
  if (endpoint === 'platform_lookup') {
    const parts = path.split('/').filter(Boolean);
    if (parts.length >= 1) {
      platform = parts[0];
    }
  }

  // Get user agent info
  const userAgent = request.headers.get('user-agent') || 'unknown';
  const isBot = /bot|crawler|spider|scraper|curl|wget|python|axios|fetch/i.test(userAgent);

  // Get country from CF headers if available
  const country = request.headers.get('cf-ipcountry') || 'unknown';

  // Authentication info
  const isAuthenticated = user ? 1 : 0;
  const userTier = user?.tier || 'anonymous';
  const userId = user?.userId || 'anonymous';

  try {
    env.ANALYTICS.writeDataPoint({
      indexes: [
        endpoint,                    // index: endpoint type (only 1 index supported despite it being an array)
      ],
      doubles: [                      // Numerical only data
        duration,                     // double1: response time in ms
        1,                           // double2: request count (for aggregation)
        response.status,             // double3: status code
        isBot ? 1 : 0,              // double4: bot flag (1=bot, 0=user)
        isAuthenticated,             // double5: authenticated flag (1=auth, 0=anon)
      ],
      blobs: [                       // String Values for filtering/grouping data
        path,                        // blob1: full path
        userAgent.substring(0, 100), // blob2: user agent (truncated)
        platform,                    // blob3: platform (for platform lookups)
        country,                     // blob4: country code
        userTier,                    // blob5: user tier (anonymous/free/pro/enterprise)
        userId.substring(0, 50),     // blob6: user ID (truncated for privacy)
      ],
    });
  } catch (error) {
    // Silently fail analytics tracking to not affect main functionality
    console.error('Analytics tracking error:', error);
  }
}

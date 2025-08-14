// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { Env } from './types';

export interface AnalyticsEvent {
  indexes?: string[];
  doubles?: number[];
  blobs?: string[];
}

export async function trackEvent(
  env: Env,
  request: Request,
  response: Response,
  startTime: number
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

  try {
    env.ANALYTICS.writeDataPoint({
      indexes: [
        endpoint,                    // index1: endpoint type
        String(response.status),      // index2: status code
        platform,                     // index3: platform (for platform lookups)
        isBot ? 'bot' : 'user',      // index4: bot or user
        country,                      // index5: country
      ],
      doubles: [
        duration,                     // double1: response time in ms
        1,                           // double2: request count (for aggregation)
      ],
      blobs: [
        path,                        // blob1: full path
        userAgent.substring(0, 100), // blob2: user agent (truncated)
      ],
    });
  } catch (error) {
    // Silently fail analytics tracking to not affect main functionality
    console.error('Analytics tracking error:', error);
  }
}
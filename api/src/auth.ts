// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { Env, AuthUser, RateLimitInfo } from './types';
import { createErrorResponse } from './utils';
import { validateApiKey } from './handlers/apikey';
import { verifyToken } from '@clerk/backend';

const CACHE_TTL = 300; // 5 minutes
const RATE_LIMIT_WINDOW = 60; // 1 minute window
const DEFAULT_RATE_LIMITS = {
  free: 100,
  pro: 1000,
  enterprise: 10000,
};

interface ClerkSession {
  userId: string;
  email?: string;
  metadata?: {
    tier?: 'free' | 'pro' | 'enterprise';
    rateLimit?: number;
  };
}

export async function verifyClerkToken(
  token: string,
  env: Env
): Promise<ClerkSession | null> {
  if (!env.CLERK_SECRET_KEY) {
    console.error('CLERK_SECRET_KEY not configured');
    return null;
  }

  // Check cache first
  const cacheKey = `auth:${token.substring(0, 20)}`; // Use first 20 chars for cache key
  const cached = await env.AUTH_CACHE.get(cacheKey, 'json');
  if (cached) {
    return cached as ClerkSession;
  }

  try {
    // Verify the JWT token using Clerk's SDK
    const result = await verifyToken(token, {
      secretKey: env.CLERK_SECRET_KEY,
      authorizedParties: env.CLERK_AUTHORIZED_PARTIES?.split(',') || ['https://ids.moe', 'http://localhost:4321'],
    });

    if (!result || !result.sub) {
      return null;
    }
    
    // Create our session object from the verified token
    const session: ClerkSession = {
      userId: result.sub, // sub is the user ID in Clerk tokens
      email: (result as any).email as string | undefined,
      metadata: {
        tier: 'free',
      },
    };

    // Cache the successful validation
    await env.AUTH_CACHE.put(
      cacheKey,
      JSON.stringify(session),
      { expirationTtl: CACHE_TTL }
    );

    return session;
  } catch (error) {
    console.error('Error verifying Clerk token:', error);
    return null;
  }
}

export async function checkRateLimit(
  userId: string,
  tier: string = 'free',
  customLimit: number | undefined,
  env: Env
): Promise<RateLimitInfo> {
  const limit = customLimit || DEFAULT_RATE_LIMITS[tier as keyof typeof DEFAULT_RATE_LIMITS] || DEFAULT_RATE_LIMITS.free;
  const now = Math.floor(Date.now() / 1000);
  const windowStart = Math.floor(now / RATE_LIMIT_WINDOW) * RATE_LIMIT_WINDOW;
  const windowKey = `rate:${userId}:${windowStart}`;

  // Get current count for this window
  const currentCount = parseInt(await env.RATE_LIMIT.get(windowKey) || '0', 10);
  
  if (currentCount >= limit) {
    return {
      remaining: 0,
      reset: windowStart + RATE_LIMIT_WINDOW,
      limit,
    };
  }

  // Increment counter
  const newCount = currentCount + 1;
  await env.RATE_LIMIT.put(
    windowKey,
    newCount.toString(),
    { expirationTtl: RATE_LIMIT_WINDOW * 2 } // Keep for 2 windows for safety
  );

  return {
    remaining: limit - newCount,
    reset: windowStart + RATE_LIMIT_WINDOW,
    limit,
  };
}

export async function authenticateRequest(
  request: Request,
  env: Env
): Promise<{ user: AuthUser | null; error: Response | null }> {
  // Get the path to check if it's an API key management endpoint
  const url = new URL(request.url);
  const path = url.pathname;
  const isApiKeyEndpoint = path === '/apikey' || path === '/apikey/regenerate';
  
  // Skip auth if not required (but API key endpoints always require auth)
  if (env.REQUIRE_AUTH !== 'true' && !isApiKeyEndpoint) {
    return { user: null, error: null };
  }

  const authHeader = request.headers.get('Authorization');
  const queryKey = url.searchParams.get('key');
  const token = authHeader?.startsWith('Bearer ') ? authHeader.substring(7) : queryKey;

  if (!token) {
    return {
      user: null,
      error: createErrorResponse(
        'Unauthorized',
        401,
        isApiKeyEndpoint 
          ? 'Missing authentication token'
          : 'Missing API key. Use: Authorization: Bearer YOUR_API_KEY or ?key=YOUR_API_KEY'
      ),
    };
  }

  let user: AuthUser | null = null;
  
  // For API key management endpoints, only accept Clerk session tokens
  if (isApiKeyEndpoint) {
    const session = await verifyClerkToken(token, env);
    if (!session) {
      return {
        user: null,
        error: createErrorResponse(
          'Unauthorized',
          401,
          'Invalid session token'
        ),
      };
    }

    user = {
      userId: session.userId,
      email: session.email,
      tier: session.metadata?.tier || 'free',
      rateLimit: session.metadata?.rateLimit,
    };
  } else {
    // For regular API endpoints, try custom API key first
    if (token.startsWith('ids_')) {
      const userId = await validateApiKey(token, env);
      if (userId) {
        // For custom API keys, we'll use default tier and rate limits
        user = {
          userId,
          tier: 'free',
        };
      }
    }
    
    // If not a valid custom key, try Clerk validation
    if (!user) {
      const session = await verifyClerkToken(token, env);
      if (!session) {
        return {
          user: null,
          error: createErrorResponse(
            'Unauthorized',
            401,
            'Invalid API key'
          ),
        };
      }

      user = {
        userId: session.userId,
        email: session.email,
        tier: session.metadata?.tier || 'free',
        rateLimit: session.metadata?.rateLimit,
      };
    }
  }

  // Check rate limit
  const rateLimitInfo = await checkRateLimit(
    user.userId,
    user.tier,
    user.rateLimit,
    env
  );

  if (rateLimitInfo.remaining <= 0) {
    const response = createErrorResponse(
      'Too Many Requests',
      429,
      `Rate limit exceeded. Limit: ${rateLimitInfo.limit} requests per minute`
    );
    response.headers.set('X-RateLimit-Limit', rateLimitInfo.limit.toString());
    response.headers.set('X-RateLimit-Remaining', '0');
    response.headers.set('X-RateLimit-Reset', rateLimitInfo.reset.toString());
    response.headers.set('Retry-After', (rateLimitInfo.reset - Math.floor(Date.now() / 1000)).toString());
    return { user: null, error: response };
  }

  // Add rate limit headers to the request for later use
  (request as any).rateLimitInfo = rateLimitInfo;

  return { user, error: null };
}

export function addRateLimitHeaders(response: Response, request: Request): Response {
  const rateLimitInfo = (request as any).rateLimitInfo as RateLimitInfo | undefined;
  if (rateLimitInfo) {
    response.headers.set('X-RateLimit-Limit', rateLimitInfo.limit.toString());
    response.headers.set('X-RateLimit-Remaining', rateLimitInfo.remaining.toString());
    response.headers.set('X-RateLimit-Reset', rateLimitInfo.reset.toString());
  }
  return response;
}
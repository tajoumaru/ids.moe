// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru

import { RouteContext } from '../types';
import { createJsonResponse, createErrorResponse } from '../utils';

interface ApiKeyData {
  userId: string;
  createdAt: number;
  lastUsed?: number;
  name?: string;
  // Only store a display version for showing masked key
  displayKey: string; // e.g., "ids_ABCD...WXYZ"
}

/**
 * Generate a secure API key
 */
function generateApiKey(): string {
  // Generate 32 bytes of random data (256 bits)
  const buffer = new Uint8Array(32);
  crypto.getRandomValues(buffer);
  // Convert to base64url format (URL-safe base64)
  const base64 = btoa(String.fromCharCode(...buffer))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  // Prefix with 'ids_' to make it identifiable
  return `ids_${base64}`;
}

/**
 * Hash an API key for storage (one-way hash)
 */
async function hashApiKey(apiKey: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(apiKey);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or create API key for a user
 */
export async function handleGetApiKey(context: RouteContext): Promise<Response> {
  const { env } = context;

  // Extract userId from the authenticated session
  // This assumes the request has already been authenticated via Clerk
  const authHeader = context.request.headers.get('Authorization');
  const sessionToken = authHeader?.replace('Bearer ', '');

  if (!sessionToken) {
    return createErrorResponse('Unauthorized', 401, 'Missing authentication token');
  }

  // Get userId from Clerk session
  // In a real implementation, you'd verify the JWT and extract the userId
  // For now, we'll use a placeholder
  const userId = context.user?.userId;

  if (!userId) {
    return createErrorResponse('Unauthorized', 401, 'Invalid session');
  }

  try {
    // Check if user already has an API key
    const existingKeyData = await env.AUTH_CACHE.get(`user:${userId}:apikey`, 'json') as ApiKeyData | null;

    if (existingKeyData) {
      // Return the display version of the key (already masked)
      return createJsonResponse({
        exists: true,
        key: existingKeyData.displayKey,
        createdAt: existingKeyData.createdAt,
        lastUsed: existingKeyData.lastUsed,
      });
    }

    // Generate new API key
    const apiKey = generateApiKey();
    const hashedKey = await hashApiKey(apiKey);
    const displayKey = `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}`;

    const keyData: ApiKeyData = {
      userId,
      createdAt: Date.now(),
      displayKey, // Only store masked version for display
    };

    // Store the key metadata indexed by user ID (WITHOUT the actual key)
    await env.AUTH_CACHE.put(`user:${userId}:apikey`, JSON.stringify(keyData));

    // Store the hashed key for validation (maps hash to userId)
    await env.AUTH_CACHE.put(`apikey:${hashedKey}`, userId);

    return createJsonResponse({
      exists: false,
      key: apiKey, // Return full key ONLY on initial generation
      createdAt: keyData.createdAt,
      message: 'New API key generated. Store it securely - it cannot be retrieved again.',
    });
  } catch (error) {
    console.error('Error handling API key request:', error);
    return createErrorResponse('Internal server error', 500, 'Failed to process API key request');
  }
}

/**
 * Regenerate API key for a user
 */
export async function handleRegenerateApiKey(context: RouteContext): Promise<Response> {
  const { env } = context;

  const userId = context.user?.userId;

  if (!userId) {
    return createErrorResponse('Unauthorized', 401, 'Invalid session');
  }

  try {
    // Note: We can't delete the old key hash because we don't store the actual key
    // The old key will simply become invalid when it's not found in the hash lookup
    // Any existing keys will stop working once we overwrite the user's key metadata

    // Generate new API key
    const apiKey = generateApiKey();
    const hashedKey = await hashApiKey(apiKey);
    const displayKey = `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}`;

    const keyData: ApiKeyData = {
      userId,
      createdAt: Date.now(),
      displayKey, // Only store masked version for display
    };

    // Store the new key metadata (WITHOUT the actual key)
    await env.AUTH_CACHE.put(`user:${userId}:apikey`, JSON.stringify(keyData));

    // Store the hashed key for validation
    await env.AUTH_CACHE.put(`apikey:${hashedKey}`, userId);

    return createJsonResponse({
      key: apiKey, // Return full key ONLY on regeneration
      createdAt: keyData.createdAt,
      message: 'API key regenerated successfully. Store it securely - it cannot be retrieved again.',
    });
  } catch (error) {
    console.error('Error regenerating API key:', error);
    return createErrorResponse('Internal server error', 500, 'Failed to regenerate API key');
  }
}

/**
 * Validate an API key
 */
export async function validateApiKey(apiKey: string, env: any): Promise<string | null> {
  try {
    const hashedKey = await hashApiKey(apiKey);
    const userId = await env.AUTH_CACHE.get(`apikey:${hashedKey}`);

    if (userId) {
      // Update last used timestamp
      const keyData = await env.AUTH_CACHE.get(`user:${userId}:apikey`, 'json') as ApiKeyData | null;
      if (keyData) {
        keyData.lastUsed = Date.now();
        await env.AUTH_CACHE.put(`user:${userId}:apikey`, JSON.stringify(keyData));
      }
    }

    return userId;
  } catch (error) {
    console.error('Error validating API key:', error);
    return null;
  }
}

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
import { handleGetApiKey, handleRegenerateApiKey } from './handlers/apikey';
import { trackEvent } from './analytics';
import { authenticateRequest, addRateLimitHeaders } from './auth';

export async function handleRequest(context: RouteContext): Promise<Response> {
	const { request } = context;
	const url = new URL(request.url);
	const path = url.pathname;
	const method = request.method;

	// Handle CORS preflight
	if (method === 'OPTIONS') {
		return createCorsResponse();
	}

	// Only allow GET and POST requests
	if (method !== 'GET' && method !== 'POST') {
		return createErrorResponse('Method not allowed', 405, 'Only GET and POST requests are allowed');
	}

	const startTime = Date.now();
	let response: Response;

	// Define public endpoints that don't require authentication
	const publicEndpoints = ['/status', '/heartbeat', '/ping', '/schema', '/schema.json', '/robots.txt', '/favicon.ico', '/mal/1'];

	// Check if authentication is required for this endpoint
	const isPublicEndpoint = publicEndpoints.includes(path);

	if (!isPublicEndpoint) {
		const { user, error } = await authenticateRequest(request, context.env);
		if (error) {
			// Track failed auth attempt
			context.ctx.waitUntil(trackEvent(context.env, request, error, startTime, undefined));
			return error;
		}
		context.user = user || undefined;
	}

	try {
		// Route matching
		switch (true) {
			case path === '/status':
				// Try to fetch from static assets first
				const statusAsset = await context.env.ASSETS.fetch(new Request(new URL('/status.json', request.url)));
				if (statusAsset.ok) {
					response = statusAsset;
				} else {
					response = await handleStatus();
				}
				break;

			case path === '/heartbeat' || path === '/ping':
				response = await handleHeartbeat(context, startTime);
				break;

			case path === '/schema' || path === '/schema.json':
				// Try to fetch from static assets first
				const schemaAsset = await context.env.ASSETS.fetch(new Request(new URL('/schema.json', request.url)));
				if (schemaAsset.ok) {
					response = schemaAsset;
				} else {
					response = await handleSchema();
				}
				break;

			case path === '/updated':
				response = await handleUpdated(context);
				break;

			case path === '/robots.txt':
				// Try to fetch from static assets first
				const robotsAsset = await context.env.ASSETS.fetch(request);
				if (robotsAsset.ok) {
					response = robotsAsset;
				} else {
					response = createTextResponse('User-agent: *\nDisallow:');
				}
				break;

			case path === '/favicon.ico':
				// Fetch from static assets
				response = await context.env.ASSETS.fetch(request);
				break;

			case path.startsWith('/trakt/'):
				response = await handleTraktRoute(context, path);
				break;

			case path.startsWith('/themoviedb/'):
				response = await handleTMDBRoute(context, path);
				break;

			case path === '/rd' || path === '/redirect':
				response = await handleRedirect(context);
				break;

			case path === '/apikey' && method === 'GET':
				// API key routes require Clerk authentication
				response = await handleGetApiKey(context);
				break;

			case path === '/apikey/regenerate' && method === 'POST':
				// API key regeneration requires Clerk authentication
				response = await handleRegenerateApiKey(context);
				break;

			default:
				// Handle platform routes
				response = await handlePlatformRoute(context, path);
				break;
		}
	} catch (error) {
		console.error('Router error:', error);
		response = createErrorResponse('Internal server error', 500, 'An unexpected error occurred');
	}

	// Add rate limit headers if applicable
	if (context.user) {
		response = addRateLimitHeaders(response, request);
	}

	// Track analytics
	context.ctx.waitUntil(trackEvent(context.env, request, response, startTime, context.user));

	return response;
}

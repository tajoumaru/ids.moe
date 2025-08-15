// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2025 tajoumaru
//
// This file is part of 'ids.moe'. It is a derivative work of
// code from the 'animeApi' project by 'nattadasu'. The original license notices
// are preserved in the `NOTICE` file in the root of this repository.

import { RouteContext, StatusResponse } from '../types';
import { checkKvHealth } from '../kv';
import { createJsonResponse, createErrorResponse, createTextResponse } from '../utils';


export async function handleStatus(): Promise<Response> {
  // This is a fallback if the static asset is not available
  return createJsonResponse({
    message: 'Status endpoint - please check static assets configuration'
  });
}

export async function handleHeartbeat(context: RouteContext, startTime: number): Promise<Response> {
  const healthCheckStart = Date.now();

  try {
    // Fast health check - just verify KV is accessible with a single lookup
    const testKey = await context.env.IDS_KV.get('myanimelist/1');

    if (!testKey) {
      return createErrorResponse(
        'Internal server error',
        500,
        'KV data is corrupted or unavailable'
      );
    }

    // Quick integrity check - verify we can get the actual data
    const testData = await context.env.IDS_KV.get(testKey);
    if (!testData) {
      return createErrorResponse(
        'Internal server error',
        500,
        'Data integrity check failed'
      );
    }

    // Verify MAL ID 1 in the data
    const parsed = JSON.parse(testData);
    if (parsed.myanimelist !== 1) {
      return createErrorResponse(
        'Internal server error',
        500,
        'Data integrity check failed'
      );
    }

    const healthCheckEnd = Date.now();
    const requestTime = (healthCheckEnd - startTime) / 1000;
    const responseTime = (healthCheckEnd - healthCheckStart) / 1000;

    const response: StatusResponse = {
      status: 'OK',
      code: 200,
      request_time: `${requestTime.toFixed(3)}s`,
      response_time: `${responseTime.toFixed(3)}s`,
      request_epoch: startTime / 1000,
    };

    return createJsonResponse(response);
  } catch (error) {
    console.error('Heartbeat handler error:', error);
    return createErrorResponse(
      'Internal server error',
      500,
      'Health check failed'
    );
  }
}

export async function handleSchema(): Promise<Response> {
  // Fallback OpenAPI schema if static asset is not available
  const fallbackSchema = {
    openapi: "3.0.3",
    info: {
      title: "ids.moe API",
      description: "High-performance anime ID mapping API providing cross-platform anime database ID relationships.",
      version: "2.0.0",
      license: {
        name: "AGPL-3.0-only",
        url: "https://github.com/tajoumaru/ids.moe/blob/main/LICENSE"
      }
    },
    servers: [{ url: "https://api.ids.moe", description: "Production server" }],
    paths: {},
    components: {
      schemas: {},
      securitySchemes: {
        apiKey: {
          type: "apiKey",
          in: "header", 
          name: "X-API-Key",
          description: "API key required for most endpoints"
        }
      }
    }
  };
  
  return createJsonResponse(fallbackSchema);
}

export async function handleUpdated(context: RouteContext): Promise<Response> {
  try {
    const lastUpdatedStr = await context.env.IDS_KV.get('last_updated');

    if (lastUpdatedStr) {
      const timestamp = parseInt(lastUpdatedStr);
      const date = new Date(timestamp * 1000);
      const formatted = date.toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'UTC',
        timeZoneName: 'short'
      });

      return createTextResponse(`Updated on ${formatted}`);
    }

    return createTextResponse('Updated endpoint - timestamp not available');
  } catch (error) {
    console.error('Updated handler error:', error);
    return createTextResponse('Updated endpoint - timestamp not available');
  }
}

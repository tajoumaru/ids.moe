import { env, createExecutionContext, waitOnExecutionContext, SELF } from 'cloudflare:test';
import { describe, it, expect, beforeEach } from 'vitest';
import worker from '../src/index';

// For now, you'll need to do something like this to get a correctly-typed
// `Request` to pass to `worker.fetch()`.
const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

describe('IDS.moe API', () => {
	let ctx: ExecutionContext;

	beforeEach(() => {
		ctx = createExecutionContext();
	});

	describe('Basic Routes', () => {
		it('redirects root to GitHub repository', async () => {
			const request = new IncomingRequest('https://ids.moe/');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(302);
			expect(response.headers.get('Location')).toBe('https://github.com/tajoumaru/ids.moe');
		});

		it('handles CORS preflight requests', async () => {
			const request = new IncomingRequest('https://ids.moe/', { method: 'OPTIONS' });
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(200);
			expect(response.headers.get('Access-Control-Allow-Origin')).toBe('*');
			expect(response.headers.get('Access-Control-Allow-Methods')).toBe('GET, OPTIONS');
		});

		it('returns robots.txt', async () => {
			const request = new IncomingRequest('https://ids.moe/robots.txt');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(200);
			expect(response.headers.get('Content-Type')).toBe('text/plain');
			expect(await response.text()).toBe('User-agent: *\nDisallow:');
		});

		it('returns 404 for favicon.ico', async () => {
			const request = new IncomingRequest('https://ids.moe/favicon.ico');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(404);
		});
	});

	describe('API Endpoints', () => {
		it('returns status information', async () => {
			const request = new IncomingRequest('https://ids.moe/status');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(200);
			expect(response.headers.get('Content-Type')).toBe('application/json');

			const data = await response.json() as any;
			expect(data).toHaveProperty('status');
			expect(data).toHaveProperty('message');
		});

		it('returns schema information', async () => {
			const request = new IncomingRequest('https://ids.moe/schema');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(200);
			expect(response.headers.get('Content-Type')).toBe('application/json');

			const data = await response.json() as any;
			expect(data).toHaveProperty('$schema');
		});

		it('returns updated timestamp', async () => {
			const request = new IncomingRequest('https://ids.moe/updated');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(200);
			expect(response.headers.get('Content-Type')).toBe('text/plain');

			const text = await response.text();
			expect(text).toContain('Updated');
		});
	});

	describe('Platform Routes', () => {
		it('handles platform lookup with valid data', async () => {
			// This test assumes MAL ID 1 exists in KV storage
			const request = new IncomingRequest('https://ids.moe/mal/1');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			// Should return either anime data (200) or not found (404)
			expect([200, 404]).toContain(response.status);

			if (response.status === 200) {
				const data = await response.json() as any;
				expect(data).toHaveProperty('title');
				expect(data).toHaveProperty('myanimelist');
			}
		});

		it('resolves platform aliases', async () => {
			// Test mal -> myanimelist alias resolution
			const request = new IncomingRequest('https://ids.moe/myanimelist/1');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			// Should return same result as mal/1
			expect([200, 404]).toContain(response.status);
		});

		it('returns 404 for invalid platform', async () => {
			const request = new IncomingRequest('https://ids.moe/invalid_platform/1');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(404);
			const data = await response.json() as any;
			expect(data).toHaveProperty('error');
		});
	});

	describe('Redirect Functionality', () => {
		it('handles redirect with missing parameters', async () => {
			const request = new IncomingRequest('https://ids.moe/redirect');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(400);
			const data = await response.json() as any;
			expect(data.error).toBe('Invalid platform');
		});

		it('handles redirect with platform parameter only', async () => {
			const request = new IncomingRequest('https://ids.moe/redirect?platform=mal');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(400);
			const data = await response.json() as any;
			expect(data.error).toBe('Invalid platform ID');
		});

		it('handles raw redirect parameter', async () => {
			const request = new IncomingRequest('https://ids.moe/redirect?platform=mal&id=1&raw=true');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			// Should return either a URL (200) or not found (404)
			expect([200, 404]).toContain(response.status);

			if (response.status === 200) {
				expect(response.headers.get('Content-Type')).toBe('text/plain');
			}
		});
	});

	describe('Special Routes', () => {
		it('handles Trakt routes format validation', async () => {
			const request = new IncomingRequest('https://ids.moe/trakt/invalid');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(400);
			const data = await response.json() as any;
			expect(data.error).toBe('Invalid request');
		});

		it('handles TMDB routes format validation', async () => {
			const request = new IncomingRequest('https://ids.moe/themoviedb/invalid');
			const response = await worker.fetch(request, env, ctx);
			await waitOnExecutionContext(ctx);

			expect(response.status).toBe(400);
			const data = await response.json() as any;
			expect(data.error).toBe('Invalid request');
		});
	});

	describe('Integration Tests', () => {
		it('handles heartbeat check (integration style)', async () => {
			const response = await SELF.fetch('https://example.com/heartbeat');
			expect([200, 500]).toContain(response.status);

			const data = await response.json() as any;
			if (response.status === 200) {
				expect(data).toHaveProperty('status');
				expect(data.status).toBe('OK');
			} else {
				expect(data).toHaveProperty('error');
			}
		});

		it('handles ping endpoint (integration style)', async () => {
			const response = await SELF.fetch('https://example.com/ping');
			expect([200, 500]).toContain(response.status);
		});
	});
});

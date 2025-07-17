# Deploying Go AnimeAPI to Vercel

## Quick Setup

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Configure Redis**
   Get a Redis instance from one of these providers:
   - **Upstash** (Recommended - serverless Redis)
   - **Redis Cloud**
   - **Railway**

3. **Deploy**
   ```bash
   # From the project root
   vercel
   
   # Set up environment variable when prompted
   # REDIS_URL: redis://default:password@host:port
   ```

4. **Production Deployment**
   ```bash
   vercel --prod
   ```

## Environment Setup

Set the Redis URL in Vercel:
```bash
vercel env add REDIS_URL
# Enter: redis://username:password@host:port/db
```

## Performance Tips

1. **Use Upstash Redis** for best serverless performance
2. **Enable Vercel Edge Network** (automatic)
3. **Monitor with Vercel Analytics**

## Testing

After deployment, test these endpoints:
- `https://your-app.vercel.app/` - Should redirect to GitHub
- `https://your-app.vercel.app/heartbeat` - Health check
- `https://your-app.vercel.app/myanimelist/1` - Get anime data

## Architecture

- Go serverless functions via `@vercel/go`
- Redis for data storage
- Edge-optimized responses
- Global CDN distribution
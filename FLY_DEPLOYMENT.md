# Fly.io Deployment Guide

## Problem Diagnosed ✅

**Root Cause**: Your app was using the wrong Dockerfile (`Dockerfile` for telegram scraper instead of `Dockerfile.fullstack` for the web app).

**Error**: `python: can't open file '/app/backend/scripts/telegram_csv_downloader.py'`

**Exit Code**: 2 (file not found)

## Solution

The `fly.toml` has been configured to use `Dockerfile.fullstack` which:
- Builds React frontend
- Copies it to Python backend
- Runs `backend/api/main.py` (FastAPI server) on port 8000
- Includes `/health` endpoint for Fly.io health checks

## Deployment Steps

### 1. Set Up Secrets
```bash
# MongoDB and API keys
./setup-fly-secrets.sh
```

### 2. Deploy the Application
```bash
# Deploy with new configuration
flyctl deploy

# Monitor deployment
flyctl logs
```

### 3. Verify Deployment
```bash
# Check status
flyctl status

# Test health endpoint
curl https://usvisachat.fly.dev/health

# Open in browser
flyctl open
```

## Important Configuration

### Environment Variables (in fly.toml)
- `LLM_PROVIDER=groq` - Uses Groq API instead of local Ollama
- `LLM_MODEL=llama-3.1-8b-instant` - Production model
- `QDRANT_HOST=qdrant.internal` - For Fly.io internal networking
- `ALLOWED_ORIGINS=https://usvisachat.fly.dev` - CORS configuration

### Secrets (via flyctl)
- `MONGODB_URI` - MongoDB Atlas connection string
- `GROQ_API_KEY` - Groq API for LLM
- `PERPLEXITY_API_KEY` - Perplexity API
- `GOOGLE_API_KEY` - Google API

## Qdrant Setup

You need to deploy Qdrant separately on Fly.io:

```bash
# Create a new app for Qdrant
flyctl apps create usvisachat-qdrant

# Deploy Qdrant from Docker Hub
flyctl deploy --image qdrant/qdrant:latest --app usvisachat-qdrant

# Create a volume for persistence
flyctl volumes create qdrant_data --size 10 --app usvisachat-qdrant
```

Then update `fly.toml`:
```toml
QDRANT_HOST = 'usvisachat-qdrant.internal'
```

## Troubleshooting

### Check Logs
```bash
flyctl logs --app usvisachat
```

### SSH into Machine
```bash
flyctl ssh console
```

### Restart Machines
```bash
flyctl machine restart --app usvisachat
```

### Scale Resources
```bash
# Increase memory if needed
flyctl scale memory 2048 --app usvisachat
```

## Cost Optimization

Current configuration:
- `auto_stop_machines = 'suspend'` - Suspends when idle
- `min_machines_running = 0` - Can scale to zero
- `memory = '1gb'` - Minimum for FastAPI + vector search
- `cpu_kind = 'shared'` - Lowest cost tier

## Next Steps

1. ✅ Deploy with fixed configuration
2. Set up Qdrant as separate Fly.io app
3. Upload vector data to Qdrant
4. Configure custom domain (optional)
5. Set up CI/CD with GitHub Actions (optional)

## Health Check Details

The `/health` endpoint returns:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "api": "running"
  }
}
```

Fly.io checks this every 15 seconds to ensure the app is running correctly.

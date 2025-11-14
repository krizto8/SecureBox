# ⚠️ Manual Redis Setup Required for Render

## Issue Fixed

The `render.yaml` blueprint has been updated because **Render doesn't support Redis in the blueprint YAML file** like it does for PostgreSQL.

## What You Need to Do

### Step 1: Deploy with Blueprint First

1. Push the updated `render.yaml` to GitHub
2. In Render dashboard, deploy from blueprint
3. This will create all services EXCEPT Redis

### Step 2: Manually Add Redis

After blueprint deployment:

1. In Render dashboard, click **"New +"** → **"Redis"**
2. Configure:
   - **Name**: `securebox-redis`
   - **Plan**: Free
   - **Region**: Same as your other services
3. Click **"Create Redis"**

### Step 3: Get Redis Connection Details

Once Redis is created:

1. Go to your Redis instance in Render
2. Copy the **Internal Redis URL** (looks like: `red-xxxxx.redis.render.com`)
3. Note the port (usually `6379`)

### Step 4: Update Environment Variables

For EACH service, manually add Redis env vars:

#### Services that need Redis:
- `securebox-api-gateway`
- `securebox-encryption`  
- `securebox-storage`
- `securebox-worker`
- `securebox-beat`

#### Add these variables to each:

```bash
REDIS_HOST=red-xxxxx.redis.render.com
REDIS_PORT=6379
```

#### For workers (securebox-worker and securebox-beat), also add:

```bash
CELERY_BROKER_URL=redis://red-xxxxx.redis.render.com:6379/1
CELERY_RESULT_BACKEND=redis://red-xxxxx.redis.render.com:6379/2
```

**Replace `red-xxxxx.redis.render.com` with YOUR actual Redis hostname!**

---

## Complete Environment Variable Checklist

### API Gateway
- ✅ `ENCRYPTION_SERVICE_URL` (auto from blueprint)
- ✅ `STORAGE_SERVICE_URL` (auto from blueprint)
- ⚠️ `REDIS_HOST` (manual - add Redis hostname)
- ✅ `REDIS_PORT=6379` (auto from blueprint)
- ✅ `SECRET_KEY` (auto-generated)
- ✅ `JWT_SECRET_KEY` (auto-generated)

### Encryption Service
- ⚠️ `REDIS_HOST` (manual - add Redis hostname)
- ✅ `REDIS_PORT=6379` (auto from blueprint)
- ✅ `ENCRYPTION_KEY_SIZE=32` (auto from blueprint)
- ✅ `RSA_KEY_SIZE=2048` (auto from blueprint)

### Storage Service
- ✅ `POSTGRES_*` (auto from blueprint)
- ⚠️ `REDIS_HOST` (manual - add Redis hostname)
- ✅ `REDIS_PORT=6379` (auto from blueprint)
- ⚠️ `MINIO_ENDPOINT` (manual - your R2 endpoint)
- ⚠️ `MINIO_ACCESS_KEY` (manual - your R2 access key)
- ⚠️ `MINIO_SECRET_KEY` (manual - your R2 secret key)
- ✅ `MINIO_BUCKET_NAME=securebox-files` (auto from blueprint)
- ✅ `MINIO_SECURE=true` (auto from blueprint)

### Background Worker
- ⚠️ `CELERY_BROKER_URL` (manual - Redis URL with /1)
- ⚠️ `CELERY_RESULT_BACKEND` (manual - Redis URL with /2)
- ⚠️ `REDIS_HOST` (manual - add Redis hostname)
- ✅ `REDIS_PORT=6379` (auto from blueprint)
- ✅ `POSTGRES_*` (auto from blueprint)
- ⚠️ `MINIO_ENDPOINT` (manual - your R2 endpoint)
- ⚠️ `MINIO_ACCESS_KEY` (manual - your R2 access key)
- ⚠️ `MINIO_SECRET_KEY` (manual - your R2 secret key)

### Celery Beat
- ⚠️ `CELERY_BROKER_URL` (manual - Redis URL with /1)
- ⚠️ `CELERY_RESULT_BACKEND` (manual - Redis URL with /2)
- ⚠️ `REDIS_HOST` (manual - add Redis hostname)
- ✅ `REDIS_PORT=6379` (auto from blueprint)
- ✅ `POSTGRES_*` (auto from blueprint)
- ⚠️ `MINIO_ENDPOINT` (manual - your R2 endpoint)
- ⚠️ `MINIO_ACCESS_KEY` (manual - your R2 access key)
- ⚠️ `MINIO_SECRET_KEY` (manual - your R2 secret key)

---

## Quick Copy-Paste Template

After creating Redis and getting the hostname, use this template:

### For API Gateway, Encryption, Storage:
```bash
REDIS_HOST=red-xxxxx.redis.render.com
```

### For Worker and Beat (add both):
```bash
REDIS_HOST=red-xxxxx.redis.render.com
CELERY_BROKER_URL=redis://red-xxxxx.redis.render.com:6379/1
CELERY_RESULT_BACKEND=redis://red-xxxxx.redis.render.com:6379/2
```

### For Storage, Worker, Beat (R2 credentials):
```bash
MINIO_ENDPOINT=71f81ec6db4437d07e8269c7bc43af20.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=your-r2-access-key
MINIO_SECRET_KEY=your-r2-secret-key
```

---

## Why This Limitation?

Render's blueprint YAML supports:
- ✅ PostgreSQL (via `databases`)
- ❌ Redis (must be created manually)

This is a Render platform limitation, not an issue with your config.

---

## Deployment Order

1. ✅ Push code to GitHub
2. ✅ Deploy blueprint (creates PostgreSQL + all services)
3. ⚠️ Create Redis manually
4. ⚠️ Add Redis env vars to all 5 services
5. ⚠️ Add R2 credentials to storage/worker/beat services
6. ✅ Services will auto-redeploy with new env vars
7. ✅ Test deployment!

---

## Verification

After adding all env vars, check each service's logs:

```bash
# Should NOT see errors like:
❌ "Connection refused" (Redis)
❌ "Can't connect to Redis"
❌ "MinIO connection failed"

# Should see:
✅ "Connected to Redis"
✅ "Database connection successful"
✅ "Service started on port XXXX"
```

---

You're almost there! Just need to manually add Redis and update those env vars. 🚀

# 🚀 Deploy SecureBox to Render.com

## Step-by-Step Deployment Guide

### Prerequisites
- GitHub account
- Your SecureBox code pushed to GitHub
- Render.com account (free to create)

---

## 📝 Deployment Steps

### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

### Step 2: Set Up File Storage (AWS S3 or Cloudflare R2)

Since Render doesn't support MinIO, you need cloud storage:

#### Option A: AWS S3 (Recommended)
1. Create AWS account (free tier available)
2. Go to S3 → Create bucket
3. Name it: `securebox-files-prod`
4. Region: Choose closest to you
5. Create IAM user with S3 access
6. Save: Access Key ID and Secret Access Key

#### Option B: Cloudflare R2 (Cheaper)
1. Go to Cloudflare R2 (10GB free)
2. Create bucket: `securebox-files`
3. Get API keys
4. Use S3-compatible endpoint

### Step 3: Deploy to Render

#### Method 1: Blueprint (One-Click Deploy) ⭐

1. Go to [render.com](https://render.com)
2. Sign in with GitHub
3. Click **"New +"** → **"Blueprint"**
4. Connect your GitHub repository
5. Render detects `render.yaml` and shows all services
6. Click **"Apply"**

#### Method 2: Manual Setup

If blueprint doesn't work:

1. **Create PostgreSQL Database**
   - New + → PostgreSQL
   - Name: `securebox-db`
   - Free tier
   - Save the connection details

2. **Create Redis**
   - New + → Redis
   - Name: `securebox-redis`
   - Free tier

3. **Create Web Services** (repeat for each):

**API Gateway:**
- New + → Web Service
- Connect GitHub repo
- Name: `securebox-api-gateway`
- Root Directory: `services/api-gateway`
- Environment: Docker
- Plan: Free
- Add environment variables (see below)

**Encryption Service:**
- Root Directory: `services/encryption-service`
- Name: `securebox-encryption`

**Storage Service:**
- Root Directory: `services/storage-service`
- Name: `securebox-storage`

4. **Create Background Services:**

**Worker:**
- New + → Background Worker
- Root Directory: `services/background-worker`
- Name: `securebox-worker`

**Celery Beat:**
- New + → Background Worker
- Root Directory: `services/background-worker`
- Docker Command: `celery -A worker beat --loglevel=info`
- Name: `securebox-beat`

### Step 4: Configure Environment Variables

For each service, add these variables in Render dashboard:

#### API Gateway
```
ENCRYPTION_SERVICE_URL=https://securebox-encryption.onrender.com
STORAGE_SERVICE_URL=https://securebox-storage.onrender.com
REDIS_HOST=<from-redis-internal-url>
REDIS_PORT=6379
SECRET_KEY=<generate-random-string>
JWT_SECRET_KEY=<generate-random-string>
```

#### Encryption Service
```
REDIS_HOST=<from-redis-internal-url>
REDIS_PORT=6379
ENCRYPTION_KEY_SIZE=32
RSA_KEY_SIZE=2048
```

#### Storage Service
```
POSTGRES_HOST=<from-postgres-internal-url>
POSTGRES_PORT=5432
POSTGRES_DB=securebox
POSTGRES_USER=<from-postgres>
POSTGRES_PASSWORD=<from-postgres>
REDIS_HOST=<from-redis-internal-url>
REDIS_PORT=6379
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=<your-aws-access-key>
MINIO_SECRET_KEY=<your-aws-secret-key>
MINIO_BUCKET_NAME=securebox-files-prod
MINIO_SECURE=true
```

#### Background Worker & Celery Beat
```
CELERY_BROKER_URL=redis://<redis-url>:6379/1
CELERY_RESULT_BACKEND=redis://<redis-url>:6379/2
REDIS_HOST=<from-redis-internal-url>
REDIS_PORT=6379
POSTGRES_HOST=<from-postgres-internal-url>
POSTGRES_PORT=5432
POSTGRES_DB=securebox
POSTGRES_USER=<from-postgres>
POSTGRES_PASSWORD=<from-postgres>
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=<your-aws-access-key>
MINIO_SECRET_KEY=<your-aws-secret-key>
MINIO_BUCKET_NAME=securebox-files-prod
```

### Step 5: Get Internal URLs

In Render, each service gets:
- **Public URL**: `https://service-name.onrender.com` (for web services)
- **Internal URL**: `service-name:port` (for service-to-service)

Copy these from each service's settings and update env vars.

### Step 6: Deploy!

1. All services will start deploying automatically
2. Monitor logs for each service
3. Check health endpoints:
   - `https://securebox-api-gateway.onrender.com/health`
   - `https://securebox-encryption.onrender.com/health`
   - `https://securebox-storage.onrender.com/health`

### Step 7: Update Frontend

Update your `web/index.html` to use the API Gateway URL:
```javascript
const API_BASE_URL = 'https://securebox-api-gateway.onrender.com';
```

### Step 8: Custom Domain (Optional)

1. Go to API Gateway service
2. Settings → Custom Domain
3. Add your domain
4. Update DNS records as shown

---

## 💰 Costs

### Free Tier (Perfect for testing):
- PostgreSQL: Free (90 day retention)
- Redis: Free (25MB)
- Web Services: Free (750 hrs/month, spins down after 15min inactive)
- Background Workers: Free (same limits)

**Total: $0/month** (with spin-down delay)

### Paid Plans (For production):
- PostgreSQL: $7/month (1GB)
- Redis: $10/month (100MB)
- Web Services: $7/month each (always-on)
- Background Workers: $7/month each

**Estimated: $40-50/month** for all services always-on

---

## 🔥 Important Notes

### Free Tier Limitations:
- Services **spin down after 15 minutes** of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- Good for testing, not production

### For Production:
- Upgrade to paid plans for always-on services
- Use AWS S3 or Cloudflare R2 for file storage
- Set up monitoring and alerts

### Service Communication:
- Use **internal URLs** for service-to-service communication (faster, free)
- Use **public URLs** only for external access

---

## 🆘 Troubleshooting

**Services won't start?**
- Check build logs in Render dashboard
- Verify Dockerfile paths are correct
- Make sure all dependencies are in requirements.txt

**Can't connect to database?**
- Use Render's provided environment variables
- Check PostgreSQL is in same region
- Verify internal URL is correct

**Redis connection fails?**
- Use internal Redis URL from Render
- Format: `redis://internal-url:6379`

**File uploads fail?**
- Verify S3 credentials are correct
- Check bucket permissions (public read, authenticated write)
- Make sure bucket region matches endpoint

**Services can't talk to each other?**
- Use internal URLs, not public
- Format: `https://service-name.onrender.com` or `http://service-name:port`

---

## 🎯 Quick Commands

Generate secret keys:
```bash
# For SECRET_KEY and JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Test deployment:
```bash
curl https://securebox-api-gateway.onrender.com/health
```

---

## 📚 Next Steps

1. Monitor deployment in Render dashboard
2. Test all endpoints
3. Upload test file to verify S3 integration
4. Set up custom domain
5. Configure monitoring (Render has built-in metrics)

---

## 🔗 Useful Links

- [Render Documentation](https://render.com/docs)
- [Blueprint Spec](https://render.com/docs/blueprint-spec)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Free Tier Limits](https://render.com/docs/free)

Need help? Render has great support and documentation!

# ☁️ Cloudflare R2 Setup for SecureBox

## Why Cloudflare R2?

- ✅ **10GB free storage** (no egress fees!)
- ✅ **S3-compatible API** (works with MinIO client)
- ✅ **Global CDN** (fast worldwide)
- ✅ **$0.015/GB/month** after free tier (cheaper than S3)
- ✅ **Zero egress charges** (unlike AWS S3)

---

## 🚀 Quick Setup Guide

### Step 1: Create Cloudflare Account

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Sign up (free account works!)
3. Navigate to **R2 Object Storage** in left sidebar

### Step 2: Create R2 Bucket

1. Click **"Create bucket"**
2. **Bucket name**: `securebox-files`
3. **Location**: Automatic (Cloudflare handles global distribution)
4. Click **"Create bucket"**

### Step 3: Generate API Token

1. In R2 dashboard, click **"Manage R2 API Tokens"**
2. Click **"Create API token"**
3. **Token name**: `SecureBox Production`
4. **Permissions**: 
   - ✅ Object Read & Write
   - ✅ Admin Read & Write (if you want bucket management)
5. **TTL**: Forever (or set expiration date)
6. **Scope to bucket** (optional): Select `securebox-files` only
7. Click **"Create API Token"**

### Step 4: Save Your Credentials

**You'll see a screen like this (SAVE IMMEDIATELY!):**

```
Access Key ID: abc123def456...
Secret Access Key: xyz789uvw012...
Endpoint for S3 clients: https://<account-id>.r2.cloudflarestorage.com
```

**⚠️ Important:** The Secret Access Key is shown **only once**! Save it now.

### Step 5: Get Your Account ID

1. Still in R2 dashboard, look at the top right
2. You'll see: `Account ID: abc123...`
3. Or check the endpoint URL, it's the part before `.r2.cloudflarestorage.com`

---

## 🔧 Configuration

### For Render Deployment

Add these environment variables to **ALL services** that need storage (storage-service, background-worker, celery-beat):

```bash
MINIO_ENDPOINT=<account-id>.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=<your-r2-access-key-id>
MINIO_SECRET_KEY=<your-r2-secret-access-key>
MINIO_BUCKET_NAME=securebox-files
MINIO_SECURE=true
```

**Example:**
```bash
MINIO_ENDPOINT=a1b2c3d4e5f6.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=1a2b3c4d5e6f7g8h9i0j
MINIO_SECRET_KEY=k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
MINIO_BUCKET_NAME=securebox-files
MINIO_SECURE=true
```

### For Local Testing

Update your `.env` file:

```bash
# Local MinIO (for development)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=securebox-files
MINIO_SECURE=false

# Cloudflare R2 (for production testing)
# MINIO_ENDPOINT=<account-id>.r2.cloudflarestorage.com
# MINIO_ACCESS_KEY=<your-r2-access-key>
# MINIO_SECRET_KEY=<your-r2-secret-key>
# MINIO_BUCKET_NAME=securebox-files
# MINIO_SECURE=true
```

---

## ✅ Verify Setup

### Test Connection (from your terminal)

```bash
# Activate your environment
source devenv/Scripts/activate  # Windows Git Bash
# or
source devenv/bin/activate      # Linux/Mac

# Test R2 connection
python -c "
from minio import Minio

client = Minio(
    '<account-id>.r2.cloudflarestorage.com',
    access_key='<your-access-key>',
    secret_key='<your-secret-key>',
    secure=True
)

# List buckets
buckets = client.list_buckets()
for bucket in buckets:
    print(f'Bucket: {bucket.name}')

print('✅ R2 connection successful!')
"
```

### Test File Upload

```bash
python -c "
from minio import Minio
from io import BytesIO

client = Minio(
    '<account-id>.r2.cloudflarestorage.com',
    access_key='<your-access-key>',
    secret_key='<your-secret-key>',
    secure=True
)

# Upload test file
data = b'Hello from SecureBox!'
client.put_object(
    'securebox-files',
    'test.txt',
    BytesIO(data),
    len(data)
)

print('✅ Test file uploaded successfully!')

# Download and verify
obj = client.get_object('securebox-files', 'test.txt')
content = obj.read()
print(f'Downloaded: {content.decode()}')

# Clean up
client.remove_object('securebox-files', 'test.txt')
print('✅ Test file deleted!')
"
```

---

## 🔒 Security Best Practices

### 1. Token Scoping
- Create separate tokens for dev/staging/prod
- Limit token permissions to specific buckets
- Set expiration dates for dev tokens

### 2. Bucket Permissions
- **Private by default** ✅ (R2 buckets are private)
- Only authenticated requests can read/write
- Enable public access only if needed (not recommended for SecureBox)

### 3. CORS Configuration (if using web uploads)

In Cloudflare R2 dashboard:
1. Select your bucket
2. Go to **Settings** → **CORS Policy**
3. Add:
```json
[
  {
    "AllowedOrigins": ["https://your-domain.com"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }
]
```

### 4. Environment Variables
- **Never commit** R2 credentials to Git
- Use Render's environment variable management
- Rotate tokens periodically

---

## 💰 Pricing & Limits

### Free Tier
- **Storage**: 10 GB/month
- **Class A Operations**: 1 million/month (write, list)
- **Class B Operations**: 10 million/month (read)
- **Egress**: Unlimited, **FREE** 🎉

### Paid (beyond free tier)
- **Storage**: $0.015/GB/month
- **Class A**: $4.50/million operations
- **Class B**: $0.36/million operations
- **Egress**: Still **FREE**!

### Example Costs
For 100GB storage, 5M reads/month:
- Storage: 90GB × $0.015 = $1.35
- Reads: 0 (within free tier)
- **Total: ~$1.35/month**

Compare to AWS S3: ~$2.30 + egress fees (~$9) = **$11.30/month**

---

## 🆚 R2 vs AWS S3

| Feature | Cloudflare R2 | AWS S3 |
|---------|--------------|--------|
| Free Storage | 10GB | 5GB (12 months) |
| Storage Cost | $0.015/GB | $0.023/GB |
| Egress | **FREE** ✅ | $0.09/GB ❌ |
| API | S3-compatible | S3 native |
| Global CDN | Yes | Extra cost |
| Speed | Fast | Fast |

**Winner for SecureBox:** R2 (cheaper, no egress fees)

---

## 🔧 Troubleshooting

### ❌ "Access Denied" Error

**Check:**
1. Endpoint URL is correct (includes `https://`)
2. Access key and secret key are correct
3. Bucket name matches exactly
4. API token has proper permissions
5. Bucket exists

### ❌ "NoSuchBucket" Error

**Solution:**
```python
# Create bucket if doesn't exist
from minio import Minio

client = Minio(...)
if not client.bucket_exists('securebox-files'):
    client.make_bucket('securebox-files')
```

### ❌ SSL Certificate Error

**Your code uses:**
```python
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
```

**Make sure:**
- `MINIO_SECURE=true` (not `True` or `1`)
- Endpoint doesn't include `https://` (just domain)

### ❌ Connection Timeout

**Check:**
1. Firewall allows outbound HTTPS (port 443)
2. Endpoint URL is correct
3. Account ID in endpoint is correct

---

## 📊 Monitoring Usage

### In Cloudflare Dashboard

1. Go to **R2** → **Overview**
2. View:
   - Storage used
   - Requests (Class A & B)
   - Current month costs

### In Your App

Add monitoring to storage service:

```python
from prometheus_client import Counter, Gauge

r2_uploads = Counter('r2_uploads_total', 'Total R2 uploads')
r2_downloads = Counter('r2_downloads_total', 'Total R2 downloads')
r2_storage_bytes = Gauge('r2_storage_bytes', 'Total bytes in R2')

# Increment on operations
r2_uploads.inc()
r2_downloads.inc()
```

---

## 🎯 Migration from MinIO to R2

If you're currently using local MinIO and want to migrate:

### 1. Backup existing files
```bash
# List all files in MinIO
mc ls myminio/securebox-files

# Mirror to R2
mc mirror myminio/securebox-files r2/securebox-files
```

### 2. Update environment variables
```bash
# Old (MinIO)
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=false

# New (R2)
MINIO_ENDPOINT=<account-id>.r2.cloudflarestorage.com
MINIO_SECURE=true
```

### 3. No code changes needed!
Your MinIO client code works as-is with R2 ✅

---

## 🚀 Ready to Deploy?

### Final Checklist

- [ ] R2 bucket created: `securebox-files`
- [ ] API token generated and saved
- [ ] Account ID noted
- [ ] Environment variables set in Render:
  - `MINIO_ENDPOINT`
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_BUCKET_NAME`
  - `MINIO_SECURE=true`
- [ ] Tested connection locally
- [ ] Updated all services (storage, worker, beat)

**You're ready to deploy!** 🎉

---

## 📚 Resources

- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)
- [R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [MinIO Python Client](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [S3 API Compatibility](https://developers.cloudflare.com/r2/api/s3/api/)

---

## 💡 Pro Tips

1. **Use R2 custom domains** for faster access (optional)
2. **Enable R2 access logs** for debugging
3. **Set lifecycle policies** to auto-delete old files (save money)
4. **Use separate buckets** for dev/staging/prod
5. **Monitor usage** to avoid surprise costs

Your SecureBox is now cloud-ready with Cloudflare R2! 🌐

# 🌐 SecureBox Cloud Deployment Guide

Deploy your SecureBox application to the cloud with these step-by-step guides.

## 🚀 Quick Deploy Options

### 1. Railway (Easiest - 5 minutes)
Railway provides the simplest deployment with automatic Docker builds.

**Steps:**
1. Push your code to GitHub
2. Go to [Railway.app](https://railway.app)
3. Connect your GitHub repo
4. Railway will auto-detect Docker and deploy!

**Configuration:**
- Add environment variables in Railway dashboard
- Railway provides PostgreSQL and Redis add-ons
- Automatic HTTPS and custom domains

### 2. Digital Ocean App Platform
**One-click deployment with managed databases.**

**Steps:**
1. Create Digital Ocean account
2. Go to App Platform
3. Connect GitHub repo
4. Choose "Docker" as build method
5. Add managed PostgreSQL and Redis

**Estimated cost:** $12-25/month

### 3. AWS ECS with Fargate
**Enterprise-grade deployment with auto-scaling.**

### 4. Google Cloud Run
**Serverless container deployment.**

### 5. Azure Container Instances
**Simple container hosting.**

## 📋 Pre-Deployment Checklist

- [ ] Code pushed to GitHub/GitLab
- [ ] Environment variables configured
- [ ] SSL certificates ready (or use platform SSL)
- [ ] Database backup strategy
- [ ] Domain name purchased (optional)

## 🔧 Environment Variables for Production

```env
# Database (use managed database URLs)
POSTGRES_HOST=your-db-host.com
POSTGRES_PORT=5432
POSTGRES_DB=securebox
POSTGRES_USER=securebox_user
POSTGRES_PASSWORD=your-strong-password

# Redis (use managed Redis)
REDIS_HOST=your-redis.com
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# MinIO/S3 (use cloud storage)
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET_NAME=securebox-files-prod
MINIO_SECURE=true

# Security
ENCRYPTION_KEY_SIZE=32
RSA_KEY_SIZE=2048

# Scaling
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=5000
```

## 🏗️ Detailed Deployment Instructions

### Option 1: Railway Deployment

1. **Prepare your repo:**
```bash
# Ensure your code is committed
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

2. **Deploy to Railway:**
- Visit [railway.app](https://railway.app)
- Click "New Project" → "Deploy from GitHub repo"
- Select your SecureBox repository
- Railway will detect Docker and start building

3. **Add services:**
- Add PostgreSQL plugin
- Add Redis plugin
- Add environment variables

4. **Configure custom domain (optional):**
- Go to project settings
- Add your domain
- Update DNS records

### Option 2: Digital Ocean App Platform

1. **Create App:**
```bash
# Install doctl CLI
# Create app.yaml configuration
```

2. **App configuration (app.yaml):**
```yaml
name: securebox
services:
- name: web
  source_dir: /
  github:
    repo: your-username/securebox
    branch: main
  dockerfile_path: Dockerfile
  http_port: 80
  instance_count: 1
  instance_size_slug: basic-xxs
  routes:
  - path: /
databases:
- engine: PG
  name: securebox-db
  size: db-s-dev-database
  version: "13"
```

### Option 3: AWS ECS Deployment

1. **Build and push Docker images:**
```bash
# Build images
docker build -t securebox-api ./services/api-gateway
docker build -t securebox-storage ./services/storage-service
docker build -t securebox-encryption ./services/encryption-service
docker build -t securebox-worker ./services/background-worker

# Tag for ECR
docker tag securebox-api:latest 123456789.dkr.ecr.region.amazonaws.com/securebox-api
docker tag securebox-storage:latest 123456789.dkr.region.amazonaws.com/securebox-storage

# Push to ECR
aws ecr get-login-password --region region | docker login --username AWS --password-stdin 123456789.dkr.ecr.region.amazonaws.com
docker push 123456789.dkr.ecr.region.amazonaws.com/securebox-api
```

2. **Create ECS Task Definition:**
```json
{
  "family": "securebox",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "api-gateway",
      "image": "your-ecr-url/securebox-api",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "POSTGRES_HOST",
          "value": "your-rds-endpoint"
        }
      ]
    }
  ]
}
```

## 🗄️ Database Options

### Managed Database Services:
- **Railway**: Built-in PostgreSQL + Redis
- **Digital Ocean**: Managed databases
- **AWS**: RDS PostgreSQL + ElastiCache Redis
- **Google Cloud**: Cloud SQL + Memorystore
- **Azure**: PostgreSQL + Redis Cache

### Storage Options:
- **AWS S3**: Replace MinIO with S3
- **Google Cloud Storage**: GCS buckets
- **Azure Blob Storage**: Azure storage
- **Digital Ocean Spaces**: S3-compatible

## 🔒 Security for Production

1. **SSL/TLS:**
   - Use platform-provided SSL (Railway, DO)
   - Or configure Let's Encrypt with Nginx

2. **Secrets Management:**
   - Use platform secret managers
   - AWS Secrets Manager
   - Azure Key Vault
   - Google Secret Manager

3. **Network Security:**
   - Configure VPC/firewall rules
   - Use private networking for databases
   - Enable DDoS protection

## 📊 Monitoring Setup

1. **Application Monitoring:**
   - Prometheus + Grafana (included)
   - Or use cloud monitoring (CloudWatch, etc.)

2. **Alerts:**
   - Set up alerts for failures
   - Monitor disk space and memory
   - Database connection monitoring

## 💰 Cost Estimates

### Railway:
- **Hobby**: Free tier available
- **Pro**: $5/month + usage
- **Database**: $5-15/month

### Digital Ocean:
- **Basic Droplet**: $12/month
- **Managed Database**: $15/month
- **Total**: ~$25-40/month

### AWS:
- **ECS Fargate**: $15-30/month
- **RDS**: $15-25/month
- **S3**: $1-5/month
- **Total**: ~$30-60/month

## 🚀 One-Click Deploy Buttons

### Deploy to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/your-template)

### Deploy to Digital Ocean
[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/your-username/securebox)

### Deploy to Heroku
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/your-username/securebox)

## 🔧 Platform-Specific Configurations

### For Railway:
```dockerfile
# Use Railway's internal networking
ENV POSTGRES_HOST=$DATABASE_URL
ENV REDIS_URL=$REDIS_URL
```

### For Heroku:
```json
{
  "name": "SecureBox",
  "description": "Encrypted file sharing platform",
  "repository": "https://github.com/your-username/securebox",
  "keywords": ["encryption", "file-sharing", "security"],
  "addons": [
    "heroku-postgresql:hobby-dev",
    "heroku-redis:hobby-dev"
  ],
  "env": {
    "ENCRYPTION_KEY_SIZE": "32",
    "RSA_KEY_SIZE": "2048"
  }
}
```

## ✅ Post-Deployment Testing

1. **Health Checks:**
```bash
curl https://your-app.com/health
curl https://your-app.com/api/health
```

2. **Upload Test:**
   - Visit your deployed app
   - Upload a test file
   - Verify encryption works
   - Test download functionality

3. **Performance Testing:**
```bash
# Load testing with curl or AB
ab -n 100 -c 10 https://your-app.com/
```

## 🆘 Troubleshooting

### Common Issues:
1. **Database Connection**: Check connection strings
2. **Memory Issues**: Increase container memory
3. **SSL Problems**: Verify certificate configuration
4. **File Upload Failures**: Check storage permissions

### Debugging Commands:
```bash
# Check logs
docker logs container-name

# Connect to container
docker exec -it container-name /bin/bash

# Check resources
docker stats
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example:
```yaml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to Railway
      uses: railway-app/deploy@v1
      with:
        token: ${{ secrets.RAILWAY_TOKEN }}
```

---

Choose the deployment option that best fits your needs and budget. Railway is recommended for beginners, while AWS/GCP are better for production workloads.

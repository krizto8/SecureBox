# 🚀 SecureBox Deployment Guide

This guide covers different deployment scenarios for the SecureBox encrypted file sharing platform.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Security Considerations](#security-considerations)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 100GB+ for production
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Software Dependencies
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Make (optional, for convenience commands)
- kubectl (for Kubernetes deployment)
- Helm 3.0+ (for Helm deployment)

## Development Setup

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/securebox.git
   cd securebox
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

3. **Generate SSL certificates (for HTTPS):**
   ```bash
   cd nginx && chmod +x generate-ssl.sh && ./generate-ssl.sh
   cd ..
   ```

4. **Start the development environment:**
   ```bash
   make dev
   # OR
   docker-compose up -d
   ```

5. **Wait for services to be ready (30-60 seconds), then test:**
   ```bash
   python test_system.py
   ```

### Development URLs
- **API Gateway**: http://localhost:5000
- **Web Interface**: Open `web/index.html` in browser
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### Development Commands

```bash
# View logs
make dev-logs

# Stop services  
make dev-stop

# Clean up everything
make dev-clean

# Build specific service
make build-api
make build-encrypt
make build-storage
make build-worker

# Run tests
make test
```

## Production Deployment

### Docker Compose Production

1. **Prepare production environment:**
   ```bash
   # Create production .env file
   cp .env.example .env.prod
   
   # Edit .env.prod with production values:
   # - Strong passwords
   # - Production database credentials
   # - Secure secret keys
   # - Proper domains
   ```

2. **Generate production SSL certificates:**
   ```bash
   # For production, use Let's Encrypt or your CA
   # Place certificates in nginx/ssl/
   ```

3. **Deploy to production:**
   ```bash
   make prod
   # OR
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Production Environment Variables

Edit `.env.prod` with production values:

```bash
# Database
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD
POSTGRES_USER=securebox_prod_user

# Security
SECRET_KEY=YOUR_SECURE_SECRET_KEY_32_CHARS_MIN
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY_32_CHARS_MIN

# MinIO
MINIO_ACCESS_KEY=YOUR_MINIO_ACCESS_KEY
MINIO_SECRET_KEY=YOUR_MINIO_SECRET_KEY_20_CHARS_MIN

# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Domain
DOMAIN=your-domain.com
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (1.20+)
- kubectl configured
- Ingress controller installed
- StorageClass configured for persistent volumes

### Basic K8s Deployment

1. **Update Kubernetes manifests:**
   ```bash
   # Edit kubernetes/00-namespace-and-config.yaml
   # Update secrets with base64 encoded values
   ```

2. **Create secrets:**
   ```bash
   # Generate base64 encoded secrets
   echo -n "your-postgres-password" | base64
   echo -n "your-secret-key" | base64
   # Update kubernetes/00-namespace-and-config.yaml
   ```

3. **Deploy to Kubernetes:**
   ```bash
   make k8s-deploy
   # OR
   kubectl apply -f kubernetes/
   ```

4. **Check deployment status:**
   ```bash
   make k8s-status
   # OR
   kubectl get all -n securebox
   ```

### Helm Deployment

1. **Customize Helm values:**
   ```bash
   # Edit helm/securebox/values.yaml
   # Update domains, storage classes, resources, etc.
   ```

2. **Install with Helm:**
   ```bash
   make helm-install
   # OR
   helm install securebox ./helm/securebox/ -n securebox --create-namespace
   ```

3. **Upgrade deployment:**
   ```bash
   make helm-upgrade
   # OR
   helm upgrade securebox ./helm/securebox/ -n securebox
   ```

### Production K8s Configuration

#### Resource Requirements
```yaml
# Minimum resources per service
api-gateway:
  requests: { memory: "256Mi", cpu: "250m" }
  limits: { memory: "512Mi", cpu: "500m" }

encryption-service:
  requests: { memory: "256Mi", cpu: "250m" }
  limits: { memory: "512Mi", cpu: "500m" }

storage-service:
  requests: { memory: "256Mi", cpu: "250m" }
  limits: { memory: "512Mi", cpu: "500m" }

postgres:
  requests: { memory: "512Mi", cpu: "500m" }
  limits: { memory: "1Gi", cpu: "1000m" }
```

#### Persistent Storage
```yaml
# Storage requirements
postgres-pvc: 20Gi (SSD recommended)
redis-pvc: 5Gi
minio-pvc: 100Gi+ (depends on usage)
```

## Security Considerations

### Secrets Management
- Use Kubernetes Secrets or external secret management
- Rotate secrets regularly
- Never commit secrets to version control

### Network Security
- Enable TLS/HTTPS everywhere
- Use network policies in Kubernetes
- Implement rate limiting
- Configure firewall rules

### Database Security
- Use strong passwords
- Enable SSL connections
- Regular backups
- Network isolation

### File Storage Security
- MinIO access control
- Bucket policies
- Encryption at rest
- Regular security audits

### Application Security
- Keep dependencies updated
- Run security scans
- Enable audit logging
- Monitor for suspicious activity

## Monitoring & Maintenance

### Health Monitoring
```bash
# Check service health
curl http://your-domain/api/health

# Kubernetes health
kubectl get pods -n securebox
kubectl describe pod <pod-name> -n securebox
```

### Metrics & Alerting
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert notifications

### Log Management
```bash
# Docker Compose logs
docker-compose logs -f [service-name]

# Kubernetes logs
kubectl logs -f deployment/api-gateway -n securebox
kubectl logs -f deployment/encryption-service -n securebox
kubectl logs -f deployment/storage-service -n securebox
```

### Backup Procedures

#### Database Backup
```bash
# Docker Compose
docker-compose exec postgres pg_dump -U securebox_user securebox > backup.sql

# Kubernetes
kubectl exec -n securebox deployment/postgres -- pg_dump -U securebox_user securebox > backup.sql
```

#### MinIO Backup
```bash
# Use MinIO client (mc) for backup
mc mirror minio/securebox-files /backup/minio/
```

### Maintenance Tasks

#### Cleanup Expired Files
```bash
# Manual trigger (runs automatically via Celery)
curl -X POST http://your-domain/api/cleanup/expired
```

#### Update Deployment
```bash
# Docker Compose
docker-compose pull
docker-compose up -d

# Kubernetes
kubectl set image deployment/api-gateway api-gateway=securebox/api-gateway:new-tag -n securebox

# Helm
helm upgrade securebox ./helm/securebox/ -n securebox
```

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check logs
docker-compose logs [service-name]
kubectl logs deployment/[service-name] -n securebox

# Check resource usage
docker stats
kubectl top pods -n securebox
```

#### Database Connection Issues
```bash
# Test database connection
docker-compose exec postgres psql -U securebox_user -d securebox -c "SELECT 1;"

# Check network connectivity
docker-compose exec api-gateway ping postgres
```

#### File Upload/Download Issues
```bash
# Check MinIO connectivity
docker-compose exec storage-service python -c "
from minio import Minio
client = Minio('minio:9000', 'minioadmin', 'minioadmin', secure=False)
print(client.bucket_exists('securebox-files'))
"
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor database performance
docker-compose exec postgres psql -U securebox_user -d securebox -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
"
```

### Debug Mode

Enable debug mode for troubleshooting:
```bash
# Set in .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

### Getting Help

1. **Check logs** for error messages
2. **Verify configuration** files
3. **Test connectivity** between services
4. **Check resource usage** (CPU, memory, disk)
5. **Review security groups/firewall** rules
6. **Consult documentation** for specific error codes

### Recovery Procedures

#### Complete System Recovery
```bash
# 1. Stop all services
docker-compose down

# 2. Backup current data
docker run --rm -v securebox_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# 3. Clean and restart
docker-compose down -v
docker-compose up -d

# 4. Restore data if needed
# ... restore procedures ...
```

## Performance Tuning

### Database Optimization
```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Redis Optimization
```bash
# Redis configuration
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Application Scaling
```yaml
# Scale services in K8s
kubectl scale deployment api-gateway --replicas=5 -n securebox
kubectl scale deployment encryption-service --replicas=3 -n securebox
kubectl scale deployment storage-service --replicas=3 -n securebox
```

---

For additional support, please check the project documentation or create an issue in the repository.

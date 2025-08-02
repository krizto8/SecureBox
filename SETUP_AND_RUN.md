# 🚀 SecureBox Setup & Run Guide

## Quick Start (Recommended)

### Prerequisites
- Docker & Docker Compose installed
- Git (to clone if needed)
- 4GB+ RAM available
- 10GB+ free disk space

### Step 1: Environment Setup
```bash
# Navigate to the project directory
cd "c:\Users\dell\Downloads\SecureBox"

# Copy environment template
cp .env.example .env

# Edit .env file (optional for development)
# The defaults should work for local development
```

### Step 2: Generate SSL Certificates (Optional for HTTPS)
```bash
# On Windows with WSL/Git Bash:
cd nginx
bash generate-ssl.sh
cd ..

# On Windows without bash, create dummy certs:
mkdir nginx\ssl
echo "dummy" > nginx\ssl\cert.pem
echo "dummy" > nginx\ssl\key.pem
```

### Step 3: Start the Application
```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait 30-60 seconds for all services to initialize
# You'll see containers starting up
```

### Step 4: Verify Installation
```bash
# Test the system
python test_system.py

# Or manually check health endpoints:
curl http://localhost:5000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Step 5: Access the Application

**Web Interface:**
- Open `web/index.html` in your web browser
- Upload files and test the encryption/decryption flow

**API Endpoints:**
- API Gateway: http://localhost:5000
- Upload endpoint: `POST http://localhost:5000/upload`
- Download endpoint: `GET http://localhost:5000/download/<token>`

**Management Interfaces:**
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- Grafana Dashboard: http://localhost:3000 (admin/admin)
- Prometheus Metrics: http://localhost:9090

---

## Alternative Setup Methods

### Method 1: Using Make Commands (If Make is available)
```bash
# Setup development environment
make setup-dev

# Start development environment
make dev

# View logs
make dev-logs

# Stop services
make dev-stop

# Clean up
make dev-clean
```

### Method 2: Manual Docker Commands
```bash
# Build all images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose stop

# Remove everything
docker-compose down -v
```

### Method 3: Running Individual Services (Advanced)

If you prefer to run services individually:

#### Start Infrastructure Services
```bash
# Start PostgreSQL
docker run -d --name securebox-postgres \
  -e POSTGRES_DB=securebox \
  -e POSTGRES_USER=securebox_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:15-alpine

# Start Redis
docker run -d --name securebox-redis \
  -p 6379:6379 \
  redis:7-alpine

# Start MinIO
docker run -d --name securebox-minio \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \
  -p 9000:9000 -p 9001:9001 \
  minio/minio server /data --console-address ":9001"
```

#### Build and Run Application Services
```bash
# Build services
docker build -t securebox/encryption-service services/encryption-service/
docker build -t securebox/storage-service services/storage-service/
docker build -t securebox/api-gateway services/api-gateway/
docker build -t securebox/background-worker services/background-worker/

# Run services
docker run -d --name encryption-service -p 8001:8001 securebox/encryption-service
docker run -d --name storage-service -p 8002:8002 securebox/storage-service
docker run -d --name api-gateway -p 5000:5000 securebox/api-gateway
docker run -d --name background-worker securebox/background-worker
```

---

## Testing the Application

### 1. Using the Web Interface
1. Open `web/index.html` in your browser
2. Select a file to upload
3. Set expiry time (1-168 hours)
4. Optional: Set a password
5. Click "Encrypt & Upload"
6. Copy the download token
7. Use the token to download the file

### 2. Using cURL Commands
```bash
# Upload a file
curl -X POST -F "file=@test.txt" -F "expiry_hours=1" \
  http://localhost:5000/upload

# Check file status (use token from upload response)
curl http://localhost:5000/status/YOUR_TOKEN_HERE

# Download file (use token from upload response)
curl -O -J http://localhost:5000/download/YOUR_TOKEN_HERE
```

### 3. Using Python Test Script
```bash
python test_system.py
```

---

## Troubleshooting

### Common Issues & Solutions

#### 1. "Port already in use" Error
```bash
# Check what's using the ports
netstat -ano | findstr :5000
netstat -ano | findstr :5432

# Stop conflicting services or change ports in docker-compose.yml
```

#### 2. Services Not Starting
```bash
# Check service logs
docker-compose logs api-gateway
docker-compose logs encryption-service
docker-compose logs storage-service
docker-compose logs postgres

# Check container status
docker-compose ps
```

#### 3. Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose exec postgres psql -U securebox_user -d securebox -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d postgres
# Wait 30 seconds, then start other services
docker-compose up -d
```

#### 4. MinIO Connection Issues
```bash
# Check MinIO status
curl http://localhost:9000/minio/health/live

# Access MinIO console to verify
# Go to http://localhost:9001 (minioadmin/minioadmin)
```

#### 5. File Upload/Download Fails
```bash
# Check all service health endpoints
curl http://localhost:5000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Check service connectivity
docker-compose exec api-gateway ping encryption-service
docker-compose exec api-gateway ping storage-service
```

### Debug Mode
```bash
# Enable debug logging
# Edit .env file:
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

---

## Production Deployment

For production deployment:

1. **Update Environment Variables:**
   ```bash
   # Edit .env with production values
   ENVIRONMENT=production
   DEBUG=false
   # Set strong passwords and secret keys
   ```

2. **Use Production Docker Compose:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Set up SSL certificates** (Let's Encrypt recommended)

4. **Configure firewall** and security groups

5. **Set up monitoring** and backups

---

## Useful Commands

```bash
# View all service status
docker-compose ps

# Follow all logs
docker-compose logs -f

# Follow specific service logs
docker-compose logs -f api-gateway

# Restart a service
docker-compose restart api-gateway

# Scale a service (if needed)
docker-compose up -d --scale api-gateway=2

# Update and restart
docker-compose pull
docker-compose up -d

# Clean up everything
docker-compose down -v
docker system prune -f
```

---

## Next Steps

1. **Test file upload/download** using the web interface
2. **Monitor system** via Grafana dashboards
3. **Review logs** for any issues
4. **Set up backups** for production use
5. **Configure SSL/HTTPS** for production
6. **Set up monitoring alerts**

The application should now be running successfully on your system!

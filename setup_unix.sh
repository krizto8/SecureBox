#!/bin/bash

echo "======================================"
echo "  SecureBox Setup Script for Linux/Mac"
echo "======================================"
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Please install Docker first:"
    echo "  Linux: https://docs.docker.com/engine/install/"
    echo "  Mac: https://docs.docker.com/desktop/mac/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed"
    echo "Please install Docker Compose:"
    echo "  https://docs.docker.com/compose/install/"
    exit 1
fi

echo "[1/5] Docker and Docker Compose are available"
echo

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "[2/5] Creating environment file..."
    cp .env.example .env
    echo "Environment file created from template"
else
    echo "[2/5] Environment file already exists"
fi
echo

# Generate SSL certificates
echo "[3/5] Setting up SSL certificates..."
cd nginx
if [ -f generate-ssl.sh ]; then
    chmod +x generate-ssl.sh
    ./generate-ssl.sh
else
    mkdir -p ssl
    echo "dummy" > ssl/cert.pem
    echo "dummy" > ssl/key.pem
    echo "SSL directory created with dummy certificates"
fi
cd ..
echo

# Start Docker services
echo "[4/5] Starting SecureBox services..."
echo "This may take a few minutes on first run..."
echo
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start services"
    echo "Check Docker daemon is running and try again"
    exit 1
fi

echo
echo "[5/5] Waiting for services to initialize..."
sleep 30

echo
echo "====================================="
echo "  SecureBox Setup Complete!"
echo "====================================="
echo
echo "Web Interface: Open web/index.html in your browser"
echo "API Gateway:   http://localhost:5000"
echo "MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "Grafana:       http://localhost:3000 (admin/admin)"
echo "Prometheus:    http://localhost:9090"
echo

# Test the system
echo "Testing the system..."
if command -v python3 &> /dev/null; then
    python3 test_system.py
elif command -v python &> /dev/null; then
    python test_system.py
else
    echo "Python not found, skipping automated tests"
    echo "You can manually test by opening web/index.html"
fi

echo
echo "Useful commands:"
echo "  docker-compose logs -f    (view logs)"
echo "  docker-compose stop       (stop services)"
echo "  docker-compose down -v    (remove everything)"
echo

echo "Setup complete! Press any key to continue..."
read -n 1 -s

# SecureBox - Encrypted File Sharing Platform
# Makefile for development and deployment

.PHONY: help build dev prod clean test lint docker-build k8s-deploy helm-install

# Default target
help:
	@echo "SecureBox - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev            - Start development environment with Docker Compose"
	@echo "  dev-build      - Build and start development environment"
	@echo "  dev-logs       - Show logs from all services"
	@echo "  dev-stop       - Stop development environment"
	@echo "  dev-clean      - Stop and remove all containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  lint           - Run linting on all services"
	@echo ""
	@echo "Build:"
	@echo "  build          - Build all Docker images"
	@echo "  build-api      - Build API Gateway image"
	@echo "  build-encrypt  - Build Encryption Service image"
	@echo "  build-storage  - Build Storage Service image"
	@echo "  build-worker   - Build Background Worker image"
	@echo ""
	@echo "Production:"
	@echo "  prod           - Deploy to production (Docker Compose)"
	@echo "  k8s-deploy     - Deploy to Kubernetes"
	@echo "  k8s-delete     - Delete Kubernetes deployment"
	@echo "  helm-install   - Install using Helm"
	@echo "  helm-upgrade   - Upgrade Helm deployment"
	@echo ""
	@echo "Utilities:"
	@echo "  ssl-certs      - Generate SSL certificates for development"
	@echo "  db-migrate     - Run database migrations"
	@echo "  db-seed        - Seed database with test data"
	@echo "  clean          - Clean up Docker resources"
	@echo "  status         - Show status of all services"

# Development Environment
dev:
	@echo "Starting SecureBox development environment..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo "Development environment is ready!"
	@echo "API Gateway: http://localhost:5000"
	@echo "MinIO Console: http://localhost:9001"
	@echo "Grafana: http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"

dev-build:
	@echo "Building and starting development environment..."
	docker-compose up -d --build
	@sleep 30
	@echo "Development environment built and ready!"

dev-logs:
	docker-compose logs -f

dev-stop:
	@echo "Stopping development environment..."
	docker-compose stop

dev-clean:
	@echo "Cleaning up development environment..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Build Docker Images
build: build-api build-encrypt build-storage build-worker
	@echo "All Docker images built successfully!"

build-api:
	@echo "Building API Gateway image..."
	docker build -t securebox/api-gateway:latest ./services/api-gateway/

build-encrypt:
	@echo "Building Encryption Service image..."
	docker build -t securebox/encryption-service:latest ./services/encryption-service/

build-storage:
	@echo "Building Storage Service image..."
	docker build -t securebox/storage-service:latest ./services/storage-service/

build-worker:
	@echo "Building Background Worker image..."
	docker build -t securebox/background-worker:latest ./services/background-worker/

# Testing
test: test-unit test-integration
	@echo "All tests completed!"

test-unit:
	@echo "Running unit tests..."
	# API Gateway tests
	cd services/api-gateway && python -m pytest tests/ -v
	# Encryption Service tests
	cd services/encryption-service && python -m pytest tests/ -v
	# Storage Service tests
	cd services/storage-service && python -m pytest tests/ -v

test-integration:
	@echo "Running integration tests..."
	cd tests && python -m pytest integration_tests/ -v

lint:
	@echo "Running linting on all services..."
	# Python linting
	cd services/api-gateway && python -m flake8 . --max-line-length=120
	cd services/encryption-service && python -m flake8 . --max-line-length=120
	cd services/storage-service && python -m flake8 . --max-line-length=120
	cd services/background-worker && python -m flake8 . --max-line-length=120

# Production Deployment
prod: build
	@echo "Deploying to production..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Production deployment complete!"

# Kubernetes Deployment
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f kubernetes/
	@echo "Kubernetes deployment initiated!"
	@echo "Check status with: kubectl get pods -n securebox"

k8s-delete:
	@echo "Deleting Kubernetes deployment..."
	kubectl delete -f kubernetes/
	@echo "Kubernetes deployment deleted!"

k8s-status:
	@echo "Kubernetes deployment status:"
	kubectl get all -n securebox

# Helm Operations
helm-install:
	@echo "Installing SecureBox with Helm..."
	helm install securebox ./helm/securebox/ -n securebox --create-namespace
	@echo "Helm installation complete!"

helm-upgrade:
	@echo "Upgrading SecureBox with Helm..."
	helm upgrade securebox ./helm/securebox/ -n securebox
	@echo "Helm upgrade complete!"

helm-uninstall:
	@echo "Uninstalling SecureBox with Helm..."
	helm uninstall securebox -n securebox
	@echo "Helm uninstallation complete!"

# SSL Certificates
ssl-certs:
	@echo "Generating SSL certificates..."
	cd nginx && chmod +x generate-ssl.sh && ./generate-ssl.sh
	@echo "SSL certificates generated!"

# Database Operations
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec postgres psql -U securebox_user -d securebox -f /docker-entrypoint-initdb.d/init.sql
	@echo "Database migrations complete!"

db-seed:
	@echo "Seeding database with test data..."
	cd scripts && python seed_database.py
	@echo "Database seeded!"

db-backup:
	@echo "Creating database backup..."
	docker-compose exec postgres pg_dump -U securebox_user securebox > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup created!"

# Utility Commands
status:
	@echo "SecureBox Service Status:"
	@echo "========================"
	docker-compose ps
	@echo ""
	@echo "Health Checks:"
	@echo "API Gateway: $$(curl -s http://localhost:5000/health | jq -r .status 2>/dev/null || echo 'Not Available')"
	@echo "Encryption Service: $$(curl -s http://localhost:8001/health | jq -r .status 2>/dev/null || echo 'Not Available')"
	@echo "Storage Service: $$(curl -s http://localhost:8002/health | jq -r .status 2>/dev/null || echo 'Not Available')"

clean:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f
	@echo "Cleanup complete!"

logs-api:
	docker-compose logs -f api-gateway

logs-encrypt:
	docker-compose logs -f encryption-service

logs-storage:
	docker-compose logs -f storage-service

logs-worker:
	docker-compose logs -f background-worker

# Performance Testing
perf-test:
	@echo "Running performance tests..."
	cd tests && python performance_test.py
	@echo "Performance tests complete!"

# Security Scan
security-scan:
	@echo "Running security scans on Docker images..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image securebox/api-gateway:latest
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image securebox/encryption-service:latest
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image securebox/storage-service:latest
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image securebox/background-worker:latest

# Monitoring
metrics:
	@echo "Opening monitoring dashboards..."
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000 manually"

# File Upload Test
test-upload:
	@echo "Testing file upload..."
	curl -X POST -F "file=@README.md" -F "expiry_hours=1" http://localhost:5000/upload

# Environment Setup
setup-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make dev"

# Documentation
docs:
	@echo "Generating API documentation..."
	cd docs && python generate_docs.py
	@echo "Documentation generated in docs/ directory"

# Version
version:
	@echo "SecureBox v1.0.0 - Encrypted File Sharing Platform"
	@echo "Built with ❤️ for secure file sharing"

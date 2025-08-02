#!/bin/bash

# SecureBox Cloud Deployment Script
# This script helps deploy SecureBox to various cloud platforms

set -e

echo "🚀 SecureBox Cloud Deployment"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Git repository not found. Please initialize git first:${NC}"
    echo "git init"
    echo "git add ."
    echo "git commit -m 'Initial commit'"
    exit 1
fi

# Check if code is committed
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Uncommitted changes detected. Committing now...${NC}"
    git add .
    git commit -m "Prepare for cloud deployment - $(date)"
fi

echo ""
echo "Select deployment platform:"
echo "1) Railway (Easiest - Free tier available)"
echo "2) Digital Ocean App Platform"
echo "3) Heroku"
echo "4) AWS ECS (Advanced)"
echo "5) Google Cloud Run"
echo "6) Custom Docker deployment"
echo ""

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo -e "${BLUE}🚂 Deploying to Railway...${NC}"
        
        # Check if Railway CLI is installed
        if ! command -v railway &> /dev/null; then
            echo -e "${YELLOW}Installing Railway CLI...${NC}"
            npm install -g @railway/cli
        fi
        
        # Login to Railway
        echo "Please login to Railway:"
        railway login
        
        # Create new project
        railway init
        
        # Add services
        echo -e "${GREEN}✅ Adding database services...${NC}"
        railway add --database postgresql
        railway add --database redis
        
        # Deploy
        echo -e "${GREEN}✅ Deploying application...${NC}"
        railway up
        
        echo -e "${GREEN}🎉 Deployment complete! Check your Railway dashboard for the URL.${NC}"
        ;;
        
    2)
        echo -e "${BLUE}🌊 Deploying to Digital Ocean...${NC}"
        
        # Check if doctl is installed
        if ! command -v doctl &> /dev/null; then
            echo -e "${RED}❌ Digital Ocean CLI (doctl) not found.${NC}"
            echo "Please install it from: https://docs.digitalocean.com/reference/doctl/how-to/install/"
            exit 1
        fi
        
        # Create app
        echo "Creating Digital Ocean App..."
        doctl apps create .do/app.yaml
        
        echo -e "${GREEN}🎉 App created! Check your Digital Ocean dashboard.${NC}"
        ;;
        
    3)
        echo -e "${BLUE}🟣 Deploying to Heroku...${NC}"
        
        # Check if Heroku CLI is installed
        if ! command -v heroku &> /dev/null; then
            echo -e "${RED}❌ Heroku CLI not found.${NC}"
            echo "Please install it from: https://devcenter.heroku.com/articles/heroku-cli"
            exit 1
        fi
        
        # Login to Heroku
        heroku login
        
        # Create app
        read -p "Enter app name (or press enter for auto-generated): " app_name
        if [ -z "$app_name" ]; then
            heroku create
        else
            heroku create "$app_name"
        fi
        
        # Add addons
        heroku addons:create heroku-postgresql:essential-0
        heroku addons:create heroku-redis:premium-0
        
        # Set stack to container
        heroku stack:set container
        
        # Deploy
        git push heroku main
        
        echo -e "${GREEN}🎉 Deployment complete!${NC}"
        heroku open
        ;;
        
    4)
        echo -e "${BLUE}☁️  AWS ECS Deployment${NC}"
        echo "This requires AWS CLI and additional setup."
        echo "Please follow the detailed guide in CLOUD_DEPLOYMENT.md"
        echo ""
        echo "Quick steps:"
        echo "1. aws configure"
        echo "2. Create ECR repositories"
        echo "3. Build and push Docker images"
        echo "4. Create ECS cluster and services"
        ;;
        
    5)
        echo -e "${BLUE}🏃 Google Cloud Run Deployment${NC}"
        echo "This requires Google Cloud SDK."
        echo "Please follow the detailed guide in CLOUD_DEPLOYMENT.md"
        ;;
        
    6)
        echo -e "${BLUE}🐳 Custom Docker Deployment${NC}"
        echo "Building production images..."
        
        # Build all images
        docker build -t securebox-api ./services/api-gateway
        docker build -t securebox-storage ./services/storage-service
        docker build -t securebox-encryption ./services/encryption-service
        docker build -t securebox-worker ./services/background-worker
        
        echo -e "${GREEN}✅ Images built successfully!${NC}"
        echo ""
        echo "To deploy to your server:"
        echo "1. Push images to your registry"
        echo "2. Copy docker-compose.prod.yml to your server"
        echo "3. Set environment variables"
        echo "4. Run: docker-compose -f docker-compose.prod.yml up -d"
        ;;
        
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🔧 Post-deployment checklist:${NC}"
echo "□ Set up custom domain (if needed)"
echo "□ Configure SSL certificates"
echo "□ Set up monitoring alerts"
echo "□ Test file upload/download"
echo "□ Configure backup strategy"
echo ""
echo -e "${BLUE}📖 For detailed instructions, see CLOUD_DEPLOYMENT.md${NC}"

@echo off
REM SecureBox Cloud Deployment Script for Windows
REM This script helps deploy SecureBox to various cloud platforms

echo 🚀 SecureBox Cloud Deployment
echo ==============================

REM Check if git is initialized
if not exist ".git" (
    echo ❌ Git repository not found. Please initialize git first:
    echo git init
    echo git add .
    echo git commit -m "Initial commit"
    exit /b 1
)

echo.
echo Select deployment platform:
echo 1) Railway (Easiest - Free tier available)
echo 2) Digital Ocean App Platform
echo 3) Heroku
echo 4) AWS ECS (Advanced)
echo 5) Google Cloud Run
echo 6) Custom Docker deployment
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo 🚂 Deploying to Railway...
    
    REM Check if Railway CLI is installed
    where railway >nul 2>&1
    if %errorlevel% neq 0 (
        echo Installing Railway CLI...
        npm install -g @railway/cli
    )
    
    echo Please login to Railway:
    railway login
    
    echo Creating new project...
    railway init
    
    echo Adding database services...
    railway add --database postgresql
    railway add --database redis
    
    echo Deploying application...
    railway up
    
    echo 🎉 Deployment complete! Check your Railway dashboard for the URL.
    
) else if "%choice%"=="2" (
    echo 🌊 Deploying to Digital Ocean...
    
    where doctl >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Digital Ocean CLI (doctl) not found.
        echo Please install it from: https://docs.digitalocean.com/reference/doctl/how-to/install/
        exit /b 1
    )
    
    echo Creating Digital Ocean App...
    doctl apps create .do\app.yaml
    
    echo 🎉 App created! Check your Digital Ocean dashboard.
    
) else if "%choice%"=="3" (
    echo 🟣 Deploying to Heroku...
    
    where heroku >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Heroku CLI not found.
        echo Please install it from: https://devcenter.heroku.com/articles/heroku-cli
        exit /b 1
    )
    
    heroku login
    
    set /p app_name="Enter app name (or press enter for auto-generated): "
    if "%app_name%"=="" (
        heroku create
    ) else (
        heroku create %app_name%
    )
    
    heroku addons:create heroku-postgresql:essential-0
    heroku addons:create heroku-redis:premium-0
    heroku stack:set container
    
    git push heroku main
    
    echo 🎉 Deployment complete!
    heroku open
    
) else if "%choice%"=="4" (
    echo ☁️ AWS ECS Deployment
    echo This requires AWS CLI and additional setup.
    echo Please follow the detailed guide in CLOUD_DEPLOYMENT.md
    
) else if "%choice%"=="5" (
    echo 🏃 Google Cloud Run Deployment
    echo This requires Google Cloud SDK.
    echo Please follow the detailed guide in CLOUD_DEPLOYMENT.md
    
) else if "%choice%"=="6" (
    echo 🐳 Custom Docker Deployment
    echo Building production images...
    
    docker build -t securebox-api ./services/api-gateway
    docker build -t securebox-storage ./services/storage-service
    docker build -t securebox-encryption ./services/encryption-service
    docker build -t securebox-worker ./services/background-worker
    
    echo ✅ Images built successfully!
    echo.
    echo To deploy to your server:
    echo 1. Push images to your registry
    echo 2. Copy docker-compose.prod.yml to your server
    echo 3. Set environment variables
    echo 4. Run: docker-compose -f docker-compose.prod.yml up -d
    
) else (
    echo ❌ Invalid choice
    exit /b 1
)

echo.
echo 🔧 Post-deployment checklist:
echo □ Set up custom domain (if needed)
echo □ Configure SSL certificates  
echo □ Set up monitoring alerts
echo □ Test file upload/download
echo □ Configure backup strategy
echo.
echo 📖 For detailed instructions, see CLOUD_DEPLOYMENT.md

pause

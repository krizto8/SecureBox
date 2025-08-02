@echo off
echo.
echo ====================================
echo   SecureBox Setup Script for Windows
echo ====================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows first
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose is not available
    echo Please ensure Docker Desktop is running
    pause
    exit /b 1
)

echo [1/5] Docker is available
echo.

REM Copy environment file if it doesn't exist
if not exist .env (
    echo [2/5] Creating environment file...
    copy .env.example .env >nul
    echo Environment file created from template
) else (
    echo [2/5] Environment file already exists
)
echo.

REM Create SSL directory and dummy certificates
echo [3/5] Setting up SSL certificates...
if not exist nginx\ssl mkdir nginx\ssl
echo dummy > nginx\ssl\cert.pem
echo dummy > nginx\ssl\key.pem
echo SSL directory created with dummy certificates
echo.

REM Start Docker services
echo [4/5] Starting SecureBox services...
echo This may take a few minutes on first run...
echo.
docker-compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start services
    echo Check Docker Desktop is running and try again
    pause
    exit /b 1
)

echo.
echo [5/5] Waiting for services to initialize...
timeout /t 30 /nobreak >nul

echo.
echo =====================================
echo   SecureBox Setup Complete!
echo =====================================
echo.
echo Web Interface: Open web\index.html in your browser
echo API Gateway:   http://localhost:5000
echo MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
echo Grafana:       http://localhost:3000 (admin/admin)
echo Prometheus:    http://localhost:9090
echo.
echo Testing the system...
python test_system.py 2>nul
if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: All tests passed! SecureBox is ready to use.
) else (
    echo.
    echo WARNING: Some tests failed. Services might still be starting up.
    echo Wait a few more minutes and run: python test_system.py
)

echo.
echo Useful commands:
echo   docker-compose logs -f    (view logs)
echo   docker-compose stop       (stop services)
echo   docker-compose down -v    (remove everything)
echo.
pause

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import redis
import jwt
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import secrets
from werkzeug.utils import secure_filename
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app,
     resources={r"/*": {"origins": "https://securebox-frontend-vbc9.onrender.com"}},
     supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE_MB', 100)) * 1024 * 1024

# Service URLs
ENCRYPTION_SERVICE_URL = os.getenv('ENCRYPTION_SERVICE_URL', 'http://localhost:8001')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://localhost:8002')

# Redis setup for rate limiting and caching
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
        decode_responses=True
    )

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}"
)
limiter.init_app(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 
    'ppt', 'pptx', 'zip', 'rar', '7z', 'mp4', 'mp3', 'wav', 'avi', 'mov'
}

# Prometheus metrics
upload_requests = Counter('securebox_uploads_total', 'Total file uploads')
download_requests = Counter('securebox_downloads_total', 'Total file downloads')
request_duration = Histogram('securebox_request_duration_seconds', 'Request duration')
active_files = Gauge('securebox_active_files', 'Number of active files')
file_sizes = Histogram('securebox_file_size_bytes', 'File sizes uploaded')
process_start_time = Gauge('securebox_process_start_time_seconds', 'Unix time when process started')

# Set process start time
process_start_time.set(time.time())

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_token():
    """Generate a secure random token for file access"""
    return secrets.token_urlsafe(32)

def generate_jwt_token(data):
    """Generate JWT token for authentication"""
    payload = {
        'data': data,
        'exp': datetime.utcnow() + timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 24)))
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload['data']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def jwt_required(f):
    """Decorator for JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        data = verify_jwt_token(token)
        if not data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.user_data = data
        return f(*args, **kwargs)
    return decorated

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint with Redis-backed persistent counters"""
    # Sync metrics with Redis for multiprocess accuracy
    try:
        # Get actual counts from database via storage service
        storage_response = requests.get(f"{STORAGE_SERVICE_URL}/stats")
        if storage_response.status_code == 200:
            stats = storage_response.json()
            # Update gauge with actual database counts
            active_files.set(stats.get('active_files', 0))
        
        # Get Redis-backed counters for accurate totals across all workers
        total_uploads = redis_client.get('metrics:uploads_total') or 0
        total_downloads = redis_client.get('metrics:downloads_total') or 0
        
        # Update counters to match Redis state (if Redis has higher values)
        current_uploads = upload_requests._value._value
        current_downloads = download_requests._value._value
        
        if int(total_uploads) > current_uploads:
            upload_requests.inc(int(total_uploads) - current_uploads)
        if int(total_downloads) > current_downloads:
            download_requests.inc(int(total_downloads) - current_downloads)
            
    except Exception as e:
        logger.warning(f"Could not sync metrics with Redis/database: {e}")
    
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_client.ping()
        
        # Check downstream services
        encryption_health = requests.get(f"{ENCRYPTION_SERVICE_URL}/health", timeout=5)
        storage_health = requests.get(f"{STORAGE_SERVICE_URL}/health", timeout=5)
        
        if encryption_health.status_code == 200 and storage_health.status_code == 200:
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'encryption': 'healthy',
                    'storage': 'healthy',
                    'redis': 'healthy'
                }
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Optional authentication endpoint"""
    data = request.get_json()
    
    # Simple demo authentication - replace with real auth
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Demo: accept any username/password combination
    user_data = {
        'username': username,
        'user_id': hashlib.sha256(username.encode()).hexdigest()[:16]
    }
    
    token = generate_jwt_token(user_data)
    
    return jsonify({
        'token': token,
        'user': user_data,
        'expires_in': int(os.getenv('JWT_EXPIRATION_HOURS', 24)) * 3600
    }), 200

@app.route('/upload', methods=["GET", "POST"])
@limiter.limit("10 per minute")
def upload_file():
    """Upload and encrypt a file"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get optional parameters
        expiry_hours = request.form.get('expiry_hours', type=int)
        if expiry_hours and expiry_hours > int(os.getenv('MAX_EXPIRY_HOURS', 168)):
            return jsonify({'error': f'Maximum expiry is {os.getenv("MAX_EXPIRY_HOURS", 168)} hours'}), 400
        
        password = request.form.get('password')  # Optional user-provided password
        
        # Generate unique identifiers
        file_id = secrets.token_hex(16)
        download_token = generate_token()
        
        # Record metrics
        upload_requests.inc()
        redis_client.incr('metrics:uploads_total')  # Redis-backed counter
        file_sizes.observe(len(file.read()))
        file.seek(0)  # Reset file pointer
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        logger.info(f"Uploading file: {file.filename}, size: {file_size} bytes")
        
        # Step 1: Encrypt the file
        encryption_response = requests.post(
            f"{ENCRYPTION_SERVICE_URL}/encrypt",
            json={
                'file_id': file_id,
                'content': file_content.hex(),  # Convert to hex for JSON transmission
                'password': password
            },
            timeout=30
        )
        
        if encryption_response.status_code != 200:
            logger.error(f"Encryption failed: {encryption_response.text}")
            return jsonify({'error': 'Encryption failed'}), 500
        
        encryption_data = encryption_response.json()
        
        # Step 2: Store the encrypted file
        storage_response = requests.post(
            f"{STORAGE_SERVICE_URL}/store",
            json={
                'file_id': file_id,
                'filename': secure_filename(file.filename),
                'encrypted_content': encryption_data['encrypted_content'],
                'encryption_key': encryption_data['encryption_key'],
                'file_size': file_size,
                'download_token': download_token,
                'expiry_hours': expiry_hours or int(os.getenv('DEFAULT_EXPIRY_HOURS', 24)),
                'content_type': file.content_type or 'application/octet-stream'
            },
            timeout=30
        )
        
        if storage_response.status_code != 200:
            logger.error(f"Storage failed: {storage_response.text}")
            return jsonify({'error': 'Storage failed'}), 500
        
        storage_data = storage_response.json()
        
        # Cache download token for quick lookup
        redis_client.setex(
            f"token:{download_token}",
            int(os.getenv('DEFAULT_EXPIRY_HOURS', 24)) * 3600,
            file_id
        )
        
        logger.info(f"File uploaded successfully: {file_id}")
        
        return jsonify({
            'file_id': file_id,
            'download_token': download_token,
            'download_url': f"/download/{download_token}",
            'filename': secure_filename(file.filename),
            'file_size': file_size,
            'expires_at': storage_data['expires_at'],
            'status': 'uploaded'
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"Service communication error: {str(e)}")
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/download/<token>', methods=['GET'])
@limiter.limit("20 per minute")
def download_file(token):
    """Download a file using one-time token"""
    try:
        # Optional password for additional security
        password = request.args.get('password')
        
        # Check if token exists and get file_id
        file_id = redis_client.get(f"token:{token}")
        if not file_id:
            return jsonify({'error': 'Invalid or expired download link'}), 404
        
        logger.info(f"Download requested for file: {file_id}")
        
        # Record download metric
        download_requests.inc()
        redis_client.incr('metrics:downloads_total')  # Redis-backed counter
        
        # Get file metadata and encrypted content from storage
        storage_response = requests.get(
            f"{STORAGE_SERVICE_URL}/retrieve/{file_id}",
            params={'token': token},
            timeout=30
        )
        
        if storage_response.status_code != 200:
            if storage_response.status_code == 404:
                return jsonify({'error': 'File not found or expired'}), 404
            return jsonify({'error': 'Storage service error'}), 500
        
        file_data = storage_response.json()
        
        # Decrypt the file
        decryption_response = requests.post(
            f"{ENCRYPTION_SERVICE_URL}/decrypt",
            json={
                'file_id': file_id,
                'encrypted_content': file_data['encrypted_content'],
                'encryption_key': file_data['encryption_key'],
                'password': password
            },
            timeout=30
        )
        
        if decryption_response.status_code != 200:
            if decryption_response.status_code == 401:
                return jsonify({'error': 'Invalid password'}), 401
            return jsonify({'error': 'Decryption failed'}), 500
        
        decrypted_data = decryption_response.json()
        
        # Convert hex back to bytes
        file_content = bytes.fromhex(decrypted_data['content'])
        
        # Mark file as downloaded (one-time use)
        requests.post(
            f"{STORAGE_SERVICE_URL}/mark_downloaded/{file_id}",
            json={'token': token},
            timeout=10
        )
        
        # Remove token from cache
        redis_client.delete(f"token:{token}")
        
        logger.info(f"File downloaded successfully: {file_id}")
        
        # Return file
        from io import BytesIO
        return send_file(
            BytesIO(file_content),
            download_name=file_data['filename'],
            as_attachment=True,
            mimetype=file_data['content_type']
        )
        
    except requests.RequestException as e:
        logger.error(f"Service communication error: {str(e)}")
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/status/<token>', methods=['GET'])
@limiter.limit("30 per minute")
def get_file_status(token):
    """Get file status and metadata"""
    try:
        # Check if token exists
        file_id = redis_client.get(f"token:{token}")
        if not file_id:
            return jsonify({'error': 'Invalid or expired token'}), 404
        
        # Get file status from storage
        storage_response = requests.get(
            f"{STORAGE_SERVICE_URL}/status/{file_id}",
            params={'token': token},
            timeout=10
        )
        
        if storage_response.status_code != 200:
            return jsonify({'error': 'File not found'}), 404
        
        return storage_response.json(), 200
        
    except requests.RequestException as e:
        logger.error(f"Service communication error: {str(e)}")
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({'error': 'Status check failed'}), 500

@app.route('/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_stats():
    """Get system statistics"""
    try:
        storage_response = requests.get(f"{STORAGE_SERVICE_URL}/stats", timeout=10)
        
        if storage_response.status_code == 200:
            return storage_response.json(), 200
        else:
            return jsonify({'error': 'Stats unavailable'}), 503
            
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Stats unavailable'}), 503

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': f'File too large. Maximum size is {os.getenv("MAX_FILE_SIZE_MB", 100)}MB'}), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('API_GATEWAY_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting API Gateway on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

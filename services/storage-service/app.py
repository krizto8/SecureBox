from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from minio import Minio
from minio.error import S3Error
import os
import logging
from datetime import datetime, timedelta
import json
import hashlib
from typing import Optional, Dict, Any
import secrets

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'securebox'),
    'user': os.getenv('POSTGRES_USER', 'securebox_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'secure_password')
}

# MinIO configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET_NAME', 'securebox-files')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# Redis setup
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                file_id VARCHAR(32) UNIQUE NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_size BIGINT NOT NULL,
                content_type VARCHAR(100),
                download_token VARCHAR(64) UNIQUE NOT NULL,
                encryption_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                downloaded_at TIMESTAMP,
                is_downloaded BOOLEAN DEFAULT FALSE,
                download_count INTEGER DEFAULT 0,
                minio_object_name VARCHAR(255) NOT NULL
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_file_id ON files(file_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_download_token ON files(download_token);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_expires_at ON files(expires_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_is_downloaded ON files(is_downloaded);")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def init_minio():
    """Initialize MinIO bucket"""
    try:
        # Create bucket if it doesn't exist
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created MinIO bucket: {MINIO_BUCKET}")
        else:
            logger.info(f"MinIO bucket exists: {MINIO_BUCKET}")
            
    except Exception as e:
        logger.error(f"MinIO initialization failed: {str(e)}")
        raise

# Initialize on startup
try:
    init_database()
    init_minio()
except Exception as e:
    logger.critical(f"Service initialization failed: {str(e)}")
    exit(1)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        # Test MinIO connection
        minio_client.bucket_exists(MINIO_BUCKET)
        
        # Test Redis connection
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': 'healthy',
                'minio': 'healthy',
                'redis': 'healthy'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/store', methods=['POST'])
def store_file():
    """Store encrypted file and metadata"""
    try:
        data = request.get_json()
        
        required_fields = ['file_id', 'filename', 'encrypted_content', 'encryption_key', 
                          'file_size', 'download_token', 'expiry_hours', 'content_type']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        file_id = data['file_id']
        filename = data['filename']
        encrypted_content = data['encrypted_content']
        encryption_key = data['encryption_key']
        file_size = data['file_size']
        download_token = data['download_token']
        expiry_hours = data['expiry_hours']
        content_type = data['content_type']
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Generate MinIO object name
        minio_object_name = f"{file_id}/{secrets.token_hex(8)}"
        
        logger.info(f"Storing file: {file_id}, size: {file_size} bytes")
        
        # Store encrypted content in MinIO
        import base64
        from io import BytesIO
        
        encrypted_bytes = base64.b64decode(encrypted_content)
        minio_client.put_object(
            MINIO_BUCKET,
            minio_object_name,
            BytesIO(encrypted_bytes),
            len(encrypted_bytes),
            content_type='application/octet-stream'
        )
        
        # Store metadata in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO files (file_id, filename, file_size, content_type, download_token, 
                             encryption_key, expires_at, minio_object_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (file_id, filename, file_size, content_type, download_token, 
              encryption_key, expires_at, minio_object_name))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Cache file metadata in Redis
        file_metadata = {
            'file_id': file_id,
            'filename': filename,
            'file_size': file_size,
            'content_type': content_type,
            'expires_at': expires_at.isoformat(),
            'minio_object_name': minio_object_name
        }
        
        redis_client.setex(
            f"file_meta:{file_id}",
            expiry_hours * 3600,
            json.dumps(file_metadata)
        )
        
        logger.info(f"File stored successfully: {file_id}")
        
        return jsonify({
            'file_id': file_id,
            'status': 'stored',
            'expires_at': expires_at.isoformat(),
            'minio_object': minio_object_name
        }), 200
        
    except S3Error as e:
        logger.error(f"MinIO storage error: {str(e)}")
        return jsonify({'error': 'Storage service error'}), 500
    except Exception as e:
        logger.error(f"Storage error: {str(e)}")
        return jsonify({'error': 'Storage failed'}), 500

@app.route('/retrieve/<file_id>', methods=['GET'])
def retrieve_file(file_id):
    """Retrieve encrypted file and metadata"""
    try:
        token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Download token required'}), 400
        
        # Get file metadata from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM files 
            WHERE file_id = %s AND download_token = %s
        """, (file_id, token))
        
        file_record = cursor.fetchone()
        
        if not file_record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'File not found or invalid token'}), 404
        
        # Check if file has expired
        if datetime.utcnow() > file_record['expires_at']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'File has expired'}), 410
        
        # Check if file has already been downloaded (one-time use)
        if file_record['is_downloaded']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'File has already been downloaded'}), 410
        
        cursor.close()
        conn.close()
        
        # Retrieve encrypted content from MinIO
        try:
            response = minio_client.get_object(MINIO_BUCKET, file_record['minio_object_name'])
            encrypted_content = response.read()
            response.close()
            
            import base64
            encrypted_content_b64 = base64.b64encode(encrypted_content).decode('utf-8')
            
        except S3Error as e:
            logger.error(f"MinIO retrieval error: {str(e)}")
            return jsonify({'error': 'File not found in storage'}), 404
        
        logger.info(f"File retrieved successfully: {file_id}")
        
        return jsonify({
            'file_id': file_id,
            'filename': file_record['filename'],
            'file_size': file_record['file_size'],
            'content_type': file_record['content_type'],
            'encrypted_content': encrypted_content_b64,
            'encryption_key': file_record['encryption_key'],
            'created_at': file_record['created_at'].isoformat(),
            'expires_at': file_record['expires_at'].isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Retrieval error: {str(e)}")
        return jsonify({'error': 'Retrieval failed'}), 500

@app.route('/mark_downloaded/<file_id>', methods=['POST'])
def mark_file_downloaded(file_id):
    """Mark file as downloaded"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Download token required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE files 
            SET is_downloaded = TRUE, downloaded_at = CURRENT_TIMESTAMP, 
                download_count = download_count + 1
            WHERE file_id = %s AND download_token = %s
        """, (file_id, token))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'File not found or invalid token'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Remove from Redis cache
        redis_client.delete(f"file_meta:{file_id}")
        
        logger.info(f"File marked as downloaded: {file_id}")
        
        return jsonify({
            'file_id': file_id,
            'status': 'downloaded',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Mark downloaded error: {str(e)}")
        return jsonify({'error': 'Operation failed'}), 500

@app.route('/status/<file_id>', methods=['GET'])
def get_file_status(file_id):
    """Get file status and metadata"""
    try:
        token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Download token required'}), 400
        
        # Try Redis cache first
        cached_meta = redis_client.get(f"file_meta:{file_id}")
        if cached_meta:
            metadata = json.loads(cached_meta)
            
            # Also get download status from database
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT is_downloaded, downloaded_at, download_count, created_at
                FROM files WHERE file_id = %s AND download_token = %s
            """, (file_id, token))
            
            db_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if db_data:
                metadata.update({
                    'is_downloaded': db_data['is_downloaded'],
                    'downloaded_at': db_data['downloaded_at'].isoformat() if db_data['downloaded_at'] else None,
                    'download_count': db_data['download_count'],
                    'created_at': db_data['created_at'].isoformat()
                })
                
                return jsonify(metadata), 200
        
        # Fall back to database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT file_id, filename, file_size, content_type, created_at, expires_at,
                   is_downloaded, downloaded_at, download_count
            FROM files WHERE file_id = %s AND download_token = %s
        """, (file_id, token))
        
        file_record = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not file_record:
            return jsonify({'error': 'File not found or invalid token'}), 404
        
        # Convert to dict and handle datetime serialization
        result = dict(file_record)
        result['created_at'] = result['created_at'].isoformat()
        result['expires_at'] = result['expires_at'].isoformat()
        if result['downloaded_at']:
            result['downloaded_at'] = result['downloaded_at'].isoformat()
        
        # Add computed status
        now = datetime.utcnow()
        expires_at = datetime.fromisoformat(result['expires_at'].replace('Z', '+00:00'))
        
        if result['is_downloaded']:
            result['status'] = 'downloaded'
        elif now > expires_at:
            result['status'] = 'expired'
        else:
            result['status'] = 'available'
            result['time_remaining'] = str(expires_at - now)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({'error': 'Status check failed'}), 500

@app.route('/cleanup/expired', methods=['POST'])
def cleanup_expired_files():
    """Clean up expired files"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find expired files
        cursor.execute("""
            SELECT file_id, minio_object_name FROM files 
            WHERE expires_at < CURRENT_TIMESTAMP AND is_downloaded = FALSE
        """)
        
        expired_files = cursor.fetchall()
        
        deleted_count = 0
        for file_record in expired_files:
            try:
                # Delete from MinIO
                minio_client.remove_object(MINIO_BUCKET, file_record['minio_object_name'])
                
                # Delete from database
                cursor.execute("DELETE FROM files WHERE file_id = %s", (file_record['file_id'],))
                
                # Remove from Redis cache
                redis_client.delete(f"file_meta:{file_record['file_id']}")
                
                deleted_count += 1
                logger.info(f"Cleaned up expired file: {file_record['file_id']}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup file {file_record['file_id']}: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'completed',
            'deleted_count': deleted_count,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({'error': 'Cleanup failed'}), 500

@app.route('/stats', methods=['GET'])
def get_storage_stats():
    """Get storage service statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get file statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_files,
                COUNT(CASE WHEN is_downloaded THEN 1 END) as downloaded_files,
                COUNT(CASE WHEN expires_at < CURRENT_TIMESTAMP THEN 1 END) as expired_files,
                COUNT(CASE WHEN expires_at >= CURRENT_TIMESTAMP AND NOT is_downloaded THEN 1 END) as active_files,
                SUM(file_size) as total_size_bytes,
                AVG(file_size) as avg_file_size_bytes
            FROM files
        """)
        
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Get MinIO bucket info
        try:
            objects = list(minio_client.list_objects(MINIO_BUCKET, recursive=True))
            minio_objects_count = len(objects)
            minio_total_size = sum(obj.size for obj in objects)
        except:
            minio_objects_count = 0
            minio_total_size = 0
        
        return jsonify({
            'service': 'storage-service',
            'database': {
                'total_files': stats[0] or 0,
                'downloaded_files': stats[1] or 0,
                'expired_files': stats[2] or 0,
                'active_files': stats[3] or 0,
                'total_size_bytes': stats[4] or 0,
                'avg_file_size_bytes': float(stats[5] or 0)
            },
            'minio': {
                'objects_count': minio_objects_count,
                'total_size_bytes': minio_total_size,
                'bucket_name': MINIO_BUCKET
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Stats unavailable'}), 500

if __name__ == '__main__':
    port = int(os.getenv('STORAGE_SERVICE_PORT', 8002))
    host = os.getenv('STORAGE_SERVICE_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Storage Service on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

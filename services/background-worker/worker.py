from celery import Celery
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from minio import Minio
from minio.error import S3Error
import os
import logging
from datetime import datetime, timedelta
import requests
import schedule
import time
import threading
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

app = Celery('securebox_worker', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# Celery configuration
app.conf.update(
    task_routes={
        'cleanup_expired_files': {'queue': 'cleanup'},
        'process_large_file': {'queue': 'processing'},
        'send_notification': {'queue': 'notifications'},
    },
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'cleanup_expired_files': {
            'task': 'background_worker.cleanup_expired_files',
            'schedule': 300.0,  # Run every 5 minutes
        },
        'cleanup_downloaded_files': {
            'task': 'background_worker.cleanup_downloaded_files',
            'schedule': 3600.0,  # Run every hour
        },
        'generate_usage_stats': {
            'task': 'background_worker.generate_usage_stats',
            'schedule': 1800.0,  # Run every 30 minutes
        },
    },
)

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

@app.task(bind=True, name='background_worker.cleanup_expired_files')
def cleanup_expired_files(self):
    """Clean up expired files from storage and database"""
    try:
        logger.info("Starting cleanup of expired files")
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find expired files
        cursor.execute("""
            SELECT file_id, minio_object_name, filename, file_size
            FROM files 
            WHERE expires_at < CURRENT_TIMESTAMP
        """)
        
        expired_files = cursor.fetchall()
        
        deleted_count = 0
        total_size_freed = 0
        
        for file_record in expired_files:
            try:
                # Delete from MinIO
                minio_client.remove_object(MINIO_BUCKET, file_record['minio_object_name'])
                
                # Log the cleanup operation
                cursor.execute("""
                    INSERT INTO file_audit_log (file_id, operation, metadata)
                    VALUES (%s, 'expired_cleanup', %s)
                """, (
                    file_record['file_id'],
                    json.dumps({
                        'filename': file_record['filename'],
                        'file_size': file_record['file_size'],
                        'cleanup_time': datetime.utcnow().isoformat()
                    })
                ))
                
                # Delete from database
                cursor.execute("DELETE FROM files WHERE file_id = %s", (file_record['file_id'],))
                
                # Remove from Redis cache
                redis_client.delete(f"file_meta:{file_record['file_id']}")
                
                deleted_count += 1
                total_size_freed += file_record['file_size']
                
                logger.info(f"Cleaned up expired file: {file_record['file_id']}")
                
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    # File already deleted from MinIO, just remove from database
                    cursor.execute("DELETE FROM files WHERE file_id = %s", (file_record['file_id'],))
                    deleted_count += 1
                    logger.warning(f"File not found in MinIO, removed from database: {file_record['file_id']}")
                else:
                    logger.error(f"Failed to delete from MinIO {file_record['file_id']}: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to cleanup file {file_record['file_id']}: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Update cleanup statistics in Redis
        cleanup_stats = {
            'last_cleanup': datetime.utcnow().isoformat(),
            'files_deleted': deleted_count,
            'bytes_freed': total_size_freed
        }
        redis_client.setex('cleanup_stats', 86400, str(cleanup_stats))  # 24 hours
        
        logger.info(f"Cleanup completed: {deleted_count} files deleted, {total_size_freed} bytes freed")
        
        return {
            'status': 'completed',
            'deleted_count': deleted_count,
            'bytes_freed': total_size_freed,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise self.retry(countdown=60, max_retries=3)

@app.task(bind=True, name='background_worker.cleanup_downloaded_files')
def cleanup_downloaded_files(self):
    """Clean up files that have been downloaded (one-time use)"""
    try:
        logger.info("Starting cleanup of downloaded files")
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find downloaded files older than 1 hour
        cursor.execute("""
            SELECT file_id, minio_object_name, filename, file_size
            FROM files 
            WHERE is_downloaded = TRUE 
            AND downloaded_at < CURRENT_TIMESTAMP - INTERVAL '1 hour'
        """)
        
        downloaded_files = cursor.fetchall()
        
        deleted_count = 0
        total_size_freed = 0
        
        for file_record in downloaded_files:
            try:
                # Delete from MinIO
                minio_client.remove_object(MINIO_BUCKET, file_record['minio_object_name'])
                
                # Log the cleanup operation
                cursor.execute("""
                    INSERT INTO file_audit_log (file_id, operation, metadata)
                    VALUES (%s, 'downloaded_cleanup', %s)
                """, (
                    file_record['file_id'],
                    json.dumps({
                        'filename': file_record['filename'],
                        'file_size': file_record['file_size'],
                        'cleanup_time': datetime.utcnow().isoformat()
                    })
                ))
                
                # Delete from database
                cursor.execute("DELETE FROM files WHERE file_id = %s", (file_record['file_id'],))
                
                # Remove from Redis cache
                redis_client.delete(f"file_meta:{file_record['file_id']}")
                
                deleted_count += 1
                total_size_freed += file_record['file_size']
                
                logger.info(f"Cleaned up downloaded file: {file_record['file_id']}")
                
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    # File already deleted from MinIO, just remove from database
                    cursor.execute("DELETE FROM files WHERE file_id = %s", (file_record['file_id'],))
                    deleted_count += 1
                    logger.warning(f"File not found in MinIO, removed from database: {file_record['file_id']}")
                else:
                    logger.error(f"Failed to delete from MinIO {file_record['file_id']}: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to cleanup downloaded file {file_record['file_id']}: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Downloaded files cleanup completed: {deleted_count} files deleted, {total_size_freed} bytes freed")
        
        return {
            'status': 'completed',
            'deleted_count': deleted_count,
            'bytes_freed': total_size_freed,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Downloaded files cleanup task failed: {str(e)}")
        raise self.retry(countdown=60, max_retries=3)

@app.task(bind=True, name='background_worker.generate_usage_stats')
def generate_usage_stats(self):
    """Generate and cache usage statistics"""
    try:
        logger.info("Generating usage statistics")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate various statistics
        stats_queries = {
            'total_files_uploaded': "SELECT COUNT(*) FROM file_audit_log WHERE operation = 'upload'",
            'total_files_downloaded': "SELECT COUNT(*) FROM file_audit_log WHERE operation = 'download'",
            'total_files_expired': "SELECT COUNT(*) FROM file_audit_log WHERE operation = 'expired_cleanup'",
            'active_files': "SELECT COUNT(*) FROM files WHERE expires_at > CURRENT_TIMESTAMP AND is_downloaded = FALSE",
            'total_storage_used': "SELECT COALESCE(SUM(file_size), 0) FROM files",
            'avg_file_size': "SELECT COALESCE(AVG(file_size), 0) FROM files",
        }
        
        stats = {}
        for stat_name, query in stats_queries.items():
            cursor.execute(query)
            stats[stat_name] = cursor.fetchone()[0]
        
        # Get hourly upload stats for last 24 hours
        cursor.execute("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as uploads
            FROM file_audit_log 
            WHERE operation = 'upload' 
            AND timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour DESC
        """)
        
        hourly_stats = cursor.fetchall()
        stats['hourly_uploads'] = [{'hour': row[0].isoformat(), 'uploads': row[1]} for row in hourly_stats]
        
        # Get file type statistics
        cursor.execute("""
            SELECT 
                SUBSTRING(content_type FROM '^[^/]+') as file_category,
                COUNT(*) as count,
                SUM(file_size) as total_size
            FROM files
            WHERE content_type IS NOT NULL
            GROUP BY SUBSTRING(content_type FROM '^[^/]+')
            ORDER BY count DESC
        """)
        
        file_type_stats = cursor.fetchall()
        stats['file_types'] = [
            {
                'category': row[0],
                'count': row[1],
                'total_size': row[2]
            } for row in file_type_stats
        ]
        
        cursor.close()
        conn.close()
        
        # Add timestamp
        stats['generated_at'] = datetime.utcnow().isoformat()
        
        # Cache statistics in Redis for 30 minutes
        import json
        redis_client.setex('usage_stats', 1800, json.dumps(stats, default=str))
        
        logger.info("Usage statistics generated and cached")
        
        return stats
        
    except Exception as e:
        logger.error(f"Usage stats generation failed: {str(e)}")
        raise self.retry(countdown=60, max_retries=3)

@app.task(bind=True, name='background_worker.process_large_file')
def process_large_file(self, file_id, processing_options=None):
    """Process large files (compression, virus scanning, etc.)"""
    try:
        logger.info(f"Processing large file: {file_id}")
        
        # This is where you could add:
        # - File compression
        # - Virus scanning
        # - File format validation
        # - Metadata extraction
        # - Image/video thumbnail generation
        
        # For now, just log the processing
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO file_audit_log (file_id, operation, metadata)
            VALUES (%s, 'processed', %s)
        """, (
            file_id,
            {
                'processing_options': processing_options or {},
                'processed_at': datetime.utcnow().isoformat()
            }
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Large file processing completed: {file_id}")
        
        return {
            'status': 'completed',
            'file_id': file_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Large file processing failed for {file_id}: {str(e)}")
        raise self.retry(countdown=120, max_retries=2)

@app.task(bind=True, name='background_worker.send_notification')
def send_notification(self, notification_type, recipient, message, metadata=None):
    """Send notifications (email, webhook, etc.)"""
    try:
        logger.info(f"Sending {notification_type} notification to {recipient}")
        
        # This is where you could integrate with:
        # - Email services (SendGrid, SES, etc.)
        # - Webhook endpoints
        # - Slack/Discord notifications
        # - SMS services
        
        # For now, just log the notification
        notification_data = {
            'type': notification_type,
            'recipient': recipient,
            'message': message,
            'metadata': metadata or {},
            'sent_at': datetime.utcnow().isoformat()
        }
        
        # Store notification in Redis for potential retry
        redis_client.lpush('sent_notifications', str(notification_data))
        redis_client.ltrim('sent_notifications', 0, 999)  # Keep last 1000 notifications
        
        logger.info(f"Notification sent successfully: {notification_type}")
        
        return notification_data
        
    except Exception as e:
        logger.error(f"Notification sending failed: {str(e)}")
        raise self.retry(countdown=60, max_retries=3)

@app.task(bind=True, name='background_worker.health_check')
def health_check_task(self):
    """Periodic health check for all services"""
    try:
        services_status = {}
        
        # Check database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            services_status['database'] = 'healthy'
        except Exception as e:
            services_status['database'] = f'unhealthy: {str(e)}'
        
        # Check MinIO
        try:
            minio_client.bucket_exists(MINIO_BUCKET)
            services_status['minio'] = 'healthy'
        except Exception as e:
            services_status['minio'] = f'unhealthy: {str(e)}'
        
        # Check Redis
        try:
            redis_client.ping()
            services_status['redis'] = 'healthy'
        except Exception as e:
            services_status['redis'] = f'unhealthy: {str(e)}'
        
        # Cache health status
        health_data = {
            'services': services_status,
            'checked_at': datetime.utcnow().isoformat()
        }
        
        redis_client.setex('health_status', 300, str(health_data))  # 5 minutes
        
        # Count unhealthy services
        unhealthy_count = sum(1 for status in services_status.values() if 'unhealthy' in status)
        
        if unhealthy_count > 0:
            logger.warning(f"Health check found {unhealthy_count} unhealthy services")
        else:
            logger.info("All services are healthy")
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check task failed: {str(e)}")
        return {
            'error': str(e),
            'checked_at': datetime.utcnow().isoformat()
        }

# Standalone scheduler for non-Celery tasks
def run_scheduler():
    """Run additional scheduled tasks outside of Celery"""
    
    def log_system_metrics():
        """Log system metrics"""
        try:
            import psutil
            
            metrics = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            redis_client.lpush('system_metrics', str(metrics))
            redis_client.ltrim('system_metrics', 0, 99)  # Keep last 100 metrics
            
            logger.info(f"System metrics logged: CPU {metrics['cpu_percent']}%, Memory {metrics['memory_percent']}%")
            
        except Exception as e:
            logger.error(f"Failed to log system metrics: {str(e)}")
    
    # Schedule additional tasks
    schedule.every(5).minutes.do(log_system_metrics)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    logger.info("Starting SecureBox Background Worker")
    
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start Celery worker
    app.start()

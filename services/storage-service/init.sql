-- Initialize SecureBox Database

-- Create database user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'securebox_user') THEN

      CREATE ROLE securebox_user LOGIN PASSWORD 'secure_password';
   END IF;
END
$do$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE securebox TO securebox_user;

-- Connect to securebox database and create tables
\c securebox;

-- Create files table
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_files_file_id ON files(file_id);
CREATE INDEX IF NOT EXISTS idx_files_download_token ON files(download_token);
CREATE INDEX IF NOT EXISTS idx_files_expires_at ON files(expires_at);
CREATE INDEX IF NOT EXISTS idx_files_is_downloaded ON files(is_downloaded);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);

-- Grant permissions on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO securebox_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO securebox_user;

-- Create audit log table for tracking file operations
CREATE TABLE IF NOT EXISTS file_audit_log (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(32) NOT NULL,
    operation VARCHAR(50) NOT NULL, -- upload, download, expire, delete
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_file_id ON file_audit_log(file_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON file_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_operation ON file_audit_log(operation);

-- Grant permissions on audit table
GRANT ALL PRIVILEGES ON file_audit_log TO securebox_user;

-- Create view for active files
CREATE OR REPLACE VIEW active_files AS
SELECT 
    file_id,
    filename,
    file_size,
    content_type,
    created_at,
    expires_at,
    download_count,
    EXTRACT(EPOCH FROM (expires_at - NOW())) AS seconds_until_expiry
FROM files
WHERE expires_at > NOW() AND is_downloaded = FALSE;

GRANT SELECT ON active_files TO securebox_user;

-- Create function to automatically clean up expired files
CREATE OR REPLACE FUNCTION cleanup_expired_files()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Insert audit records for files being deleted
    INSERT INTO file_audit_log (file_id, operation, metadata)
    SELECT 
        file_id, 
        'expire',
        json_build_object(
            'filename', filename,
            'expired_at', expires_at,
            'was_downloaded', is_downloaded
        )
    FROM files 
    WHERE expires_at < NOW();
    
    -- Delete expired files
    DELETE FROM files WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to log file operations
CREATE OR REPLACE FUNCTION log_file_operation(
    p_file_id VARCHAR(32),
    p_operation VARCHAR(50),
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO file_audit_log (file_id, operation, ip_address, user_agent, metadata)
    VALUES (p_file_id, p_operation, p_ip_address, p_user_agent, p_metadata);
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION cleanup_expired_files() TO securebox_user;
GRANT EXECUTE ON FUNCTION log_file_operation(VARCHAR(32), VARCHAR(50), INET, TEXT, JSONB) TO securebox_user;

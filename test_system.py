#!/usr/bin/env python3
"""
SecureBox System Test Script
Tests the complete file upload/download flow
"""

import requests
import json
import time
import os
import hashlib
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:5000"
TEST_FILE_CONTENT = b"Hello SecureBox! This is a test file content for encryption and secure sharing."
TEST_FILENAME = "test_file.txt"

def log(message):
    """Log messages with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def test_health_checks():
    """Test all service health endpoints"""
    log("Testing health checks...")
    
    services = [
        ("API Gateway", f"{API_BASE_URL}/health"),
        ("Encryption Service", "http://localhost:8001/health"),
        ("Storage Service", "http://localhost:8002/health"),
    ]
    
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                log(f"✅ {service_name} is healthy")
            else:
                log(f"❌ {service_name} health check failed: {response.status_code}")
                return False
        except Exception as e:
            log(f"❌ {service_name} health check failed: {str(e)}")
            return False
    
    return True

def test_file_upload():
    """Test file upload functionality"""
    log("Testing file upload...")
    
    # Create a temporary test file
    with open(TEST_FILENAME, "wb") as f:
        f.write(TEST_FILE_CONTENT)
    
    try:
        # Upload the file
        with open(TEST_FILENAME, "rb") as f:
            files = {"file": (TEST_FILENAME, f, "text/plain")}
            data = {"expiry_hours": 1}
            
            response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            upload_result = response.json()
            log("✅ File uploaded successfully")
            log(f"   File ID: {upload_result['file_id']}")
            log(f"   Download Token: {upload_result['download_token']}")
            log(f"   Download URL: {upload_result['download_url']}")
            return upload_result
        else:
            log(f"❌ File upload failed: {response.status_code}")
            log(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        log(f"❌ File upload error: {str(e)}")
        return None
    finally:
        # Clean up test file
        if os.path.exists(TEST_FILENAME):
            os.remove(TEST_FILENAME)

def test_file_status(upload_result):
    """Test file status check"""
    log("Testing file status check...")
    
    try:
        token = upload_result['download_token']
        response = requests.get(f"{API_BASE_URL}/status/{token}")
        
        if response.status_code == 200:
            status_result = response.json()
            log("✅ File status retrieved successfully")
            log(f"   Status: {status_result.get('status', 'unknown')}")
            log(f"   Filename: {status_result.get('filename', 'unknown')}")
            log(f"   Size: {status_result.get('file_size', 0)} bytes")
            return True
        else:
            log(f"❌ File status check failed: {response.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ File status error: {str(e)}")
        return False

def test_file_download(upload_result):
    """Test file download functionality"""
    log("Testing file download...")
    
    try:
        token = upload_result['download_token']
        response = requests.get(f"{API_BASE_URL}/download/{token}")
        
        if response.status_code == 200:
            downloaded_content = response.content
            
            # Verify content matches original
            if downloaded_content == TEST_FILE_CONTENT:
                log("✅ File downloaded successfully and content matches!")
                return True
            else:
                log("❌ Downloaded content doesn't match original")
                return False
        else:
            log(f"❌ File download failed: {response.status_code}")
            log(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        log(f"❌ File download error: {str(e)}")
        return False

def test_one_time_download(upload_result):
    """Test one-time download functionality"""
    log("Testing one-time download restriction...")
    
    try:
        token = upload_result['download_token']
        
        # First download should work
        response1 = requests.get(f"{API_BASE_URL}/download/{token}")
        
        # Second download should fail
        time.sleep(1)  # Brief pause
        response2 = requests.get(f"{API_BASE_URL}/download/{token}")
        
        if response1.status_code == 200 and response2.status_code in [404, 410]:
            log("✅ One-time download restriction working correctly")
            return True
        else:
            log(f"❌ One-time download restriction failed")
            log(f"   First download: {response1.status_code}")
            log(f"   Second download: {response2.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ One-time download test error: {str(e)}")
        return False

def test_password_protection():
    """Test password-protected file upload/download"""
    log("Testing password-protected file...")
    
    password = "test_password_123"
    
    # Create a temporary test file
    with open(TEST_FILENAME, "wb") as f:
        f.write(TEST_FILE_CONTENT)
    
    try:
        # Upload the file with password
        with open(TEST_FILENAME, "rb") as f:
            files = {"file": (TEST_FILENAME, f, "text/plain")}
            data = {"expiry_hours": 1, "password": password}
            
            response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            upload_result = response.json()
            log("✅ Password-protected file uploaded successfully")
            
            # Test download with correct password
            token = upload_result['download_token']
            response = requests.get(f"{API_BASE_URL}/download/{token}", params={"password": password})
            
            if response.status_code == 200 and response.content == TEST_FILE_CONTENT:
                log("✅ Password-protected download successful")
                return True
            else:
                log(f"❌ Password-protected download failed: {response.status_code}")
                return False
        else:
            log(f"❌ Password-protected upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ Password protection test error: {str(e)}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(TEST_FILENAME):
            os.remove(TEST_FILENAME)

def test_system_stats():
    """Test system statistics endpoint"""
    log("Testing system statistics...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        
        if response.status_code == 200:
            stats = response.json()
            log("✅ System statistics retrieved")
            log(f"   Database files: {stats.get('database', {}).get('total_files', 'N/A')}")
            log(f"   Active files: {stats.get('database', {}).get('active_files', 'N/A')}")
            return True
        else:
            log(f"❌ System statistics failed: {response.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ System statistics error: {str(e)}")
        return False

def main():
    """Run all tests"""
    log("🔐 SecureBox System Test Suite")
    log("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Health checks
    total_tests += 1
    if test_health_checks():
        tests_passed += 1
    
    log("")
    
    # Upload and download test
    total_tests += 1
    upload_result = test_file_upload()
    if upload_result:
        tests_passed += 1
        
        # Status check
        total_tests += 1
        if test_file_status(upload_result):
            tests_passed += 1
        
        # One-time download test (using a fresh upload)
        log("")
        total_tests += 1
        fresh_upload = test_file_upload()
        if fresh_upload and test_one_time_download(fresh_upload):
            tests_passed += 1
    
    log("")
    
    # Password protection test
    total_tests += 1
    if test_password_protection():
        tests_passed += 1
    
    log("")
    
    # System stats test
    total_tests += 1
    if test_system_stats():
        tests_passed += 1
    
    # Results
    log("")
    log("=" * 50)
    log(f"Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        log("🎉 All tests passed! SecureBox is working correctly.")
        return 0
    else:
        log("❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

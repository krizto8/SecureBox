#!/bin/bash

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate for development
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=SecureBox/OU=Development/CN=securebox.local"

echo "SSL certificates generated for development use"
echo "Certificate: ssl/cert.pem"
echo "Private Key: ssl/key.pem"

# Set appropriate permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

echo "SSL setup complete!"

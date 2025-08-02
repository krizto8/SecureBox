#!/bin/bash

echo "🚀 Generating SecureBox monitoring activity..."

# Create different test files
echo "Small test file" > small.txt
echo "This is a medium sized test file with more content to make it larger" > medium.txt
echo "Large test file content here. Adding lots of text to make this file bigger. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris." > large.txt

echo "📤 Uploading files..."

# Upload files
UPLOAD1=$(curl -s -X POST -F "file=@small.txt" -F "expiry_hours=1" http://localhost:5000/upload)
UPLOAD2=$(curl -s -X POST -F "file=@medium.txt" -F "expiry_hours=2" http://localhost:5000/upload)  
UPLOAD3=$(curl -s -X POST -F "file=@large.txt" -F "expiry_hours=3" http://localhost:5000/upload)

# Extract download tokens
TOKEN1=$(echo $UPLOAD1 | python -c "import sys, json; print(json.load(sys.stdin)['download_token'])")
TOKEN2=$(echo $UPLOAD2 | python -c "import sys, json; print(json.load(sys.stdin)['download_token'])")
TOKEN3=$(echo $UPLOAD3 | python -c "import sys, json; print(json.load(sys.stdin)['download_token'])")

echo "📥 Downloading files..."

# Download files to generate download metrics
curl -s http://localhost:5000/download/$TOKEN1 > /dev/null
sleep 2
curl -s http://localhost:5000/download/$TOKEN2 > /dev/null  
sleep 2
curl -s http://localhost:5000/download/$TOKEN3 > /dev/null

echo "✅ Activity generated! Check your dashboards:"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3000"

# Show current metrics
echo ""
echo "📊 Current Metrics:"
curl -s http://localhost:5000/metrics | grep -E "securebox_(uploads|downloads|file_size)" | grep -v "_created"

# Cleanup
rm -f small.txt medium.txt large.txt

echo ""
echo "🎯 Try these Prometheus queries:"
echo "   securebox_uploads_total"
echo "   rate(securebox_uploads_total[5m])" 
echo "   securebox_file_size_bytes_sum"

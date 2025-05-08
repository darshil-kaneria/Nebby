#!/bin/bash
# capture_video.sh - Fixed script to capture video traffic with Chrome

# Usage: ./capture_video.sh <video_url> <output_directory>

url=$1
output_dir=${2:-"../measurements"}

if [ -z "$url" ]; then
    echo "Usage: ./capture_video.sh <video_url> [output_directory]"
    echo "Example: ./capture_video.sh https://www.youtube.com/watch?v=dQw4w9WgXcQ ../measurements"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$output_dir"

# Set up temporary directory
temp_dir="/tmp/chrome_capture"
rm -rf "$temp_dir"  # Clean up any previous runs
mkdir -p "$temp_dir"
log_file="$temp_dir/chrome_netlog.json"

echo "===== Starting Direct Video Capture ====="
echo "URL: $url"
echo "Output directory: $output_dir"
echo "Temporary directory: $temp_dir"

# Launch Chrome first with a different log path
echo "Starting Chrome pre-run to warm up cache..."
chrome_log="$temp_dir/chrome.log"
google-chrome --headless --no-sandbox --disable-gpu \
  --user-data-dir="$temp_dir/chrome_data" \
  "$url" > "$chrome_log" 2>&1 &
pre_chrome_pid=$!

# Give Chrome time to initialize and load page
echo "Waiting for Chrome to initialize..."
sleep 5

# Kill the pre-run Chrome
echo "Stopping pre-run Chrome..."
kill $pre_chrome_pid
wait $pre_chrome_pid 2>/dev/null
sleep 2

# Start packet capture
echo "Starting packet capture..."
sudo tcpdump -i any -w "$temp_dir/capture.pcap" port 80 or port 443 &
tcpdump_pid=$!

# Allow tcpdump to initialize
sleep 2

# Launch Chrome with logging enabled
echo "Launching Chrome with network logging..."
google-chrome --headless --no-sandbox --disable-gpu \
  --autoplay-policy=no-user-gesture-required \
  --log-net-log="$log_file" \
  --net-log-capture-mode=IncludeCookiesAndCredentials \
  --user-data-dir="$temp_dir/chrome_data" \
  "$url" > "$chrome_log" 2>&1 &
chrome_pid=$!

# Let Chrome run for 30 seconds
echo "Capturing video traffic for 30 seconds..."
duration=30
sleep $duration

# IMPORTANT: Gracefully stop Chrome
echo "Gracefully stopping Chrome..."
# First send SIGTERM for clean shutdown
kill -SIGTERM $chrome_pid
# Wait a bit for Chrome to clean up
sleep 5
# Check if process is still running
if ps -p $chrome_pid > /dev/null; then
    echo "Chrome still running, using SIGKILL..."
    kill -SIGKILL $chrome_pid
fi
wait $chrome_pid 2>/dev/null

# Wait for Chrome to fully exit and logs to be written
echo "Waiting for log files to be finalized..."
sleep 10

# Stop packet capture
echo "Stopping packet capture..."
sudo kill -SIGTERM $tcpdump_pid
sleep 2
if ps -p $tcpdump_pid > /dev/null; then
    sudo kill -SIGKILL $tcpdump_pid
fi
wait $tcpdump_pid 2>/dev/null

# Fix JSON if needed
echo "Checking network log file..."
if [ -f "$log_file" ]; then
    echo "Network log found at $log_file"
    echo "File size: $(du -h "$log_file" | cut -f1)"
    
    # Check if the JSON is valid and fix if needed
    if ! python -m json.tool "$log_file" > /dev/null 2>&1; then
        echo "JSON appears to be invalid, attempting to fix..."
        # Create a valid JSON by adding closing bracket if needed
        sed -i -e '$s/,$//' -e '$a}' "$log_file"
        if python -m json.tool "$log_file" > /dev/null 2>&1; then
            echo "JSON successfully fixed"
        else
            echo "Could not fix JSON, creating minimal valid JSON"
            echo '{"events":[]}' > "$log_file"
        fi
    else
        echo "JSON is valid"
    fi
    
    # Copy network log
    cp "$log_file" "$output_dir/chrome_netlog.json"
    echo "Network log copied to $output_dir/chrome_netlog.json"
else
    echo "ERROR: Network log not found at $log_file"
    # Check if the directory exists
    if [ -d "$temp_dir" ]; then
        echo "Temporary directory exists, but log file is missing"
        echo "Directory contents:"
        ls -la "$temp_dir"
    else
        echo "Temporary directory does not exist"
    fi
    # Create a minimal valid JSON
    echo '{"events":[]}' > "$output_dir/chrome_netlog.json"
    echo "Created minimal valid JSON file"
fi

# Process the PCAP file
echo "Processing PCAP file..."
if [ -f "$temp_dir/capture.pcap" ]; then
    echo "PCAP file size: $(du -h "$temp_dir/capture.pcap" | cut -f1)"
    
    # Use tshark to extract TCP information with more fields
    tshark -r "$temp_dir/capture.pcap" -T fields \
      -e frame.time_relative \
      -e ip.src -e tcp.srcport \
      -e ip.dst -e tcp.dstport \
      -e tcp.seq -e tcp.ack \
      -E header=y -E separator=, -E quote=d > "$output_dir/video_tcp.csv"
      
    echo "TCP data extracted to $output_dir/video_tcp.csv"
else
    echo "ERROR: PCAP file not found"
fi

echo "===== Video Capture Complete ====="
echo "Output files:"
echo "  Network log: $output_dir/chrome_netlog.json"
echo "  TCP data: $output_dir/video_tcp.csv"
echo "  Chrome log: $chrome_log"
echo "All temporary files in: $temp_dir"
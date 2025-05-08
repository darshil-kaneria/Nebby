#!/bin/bash
# Modified client.sh to support both wget and Chrome for video

sudo ifconfig ingress mtu 100
sudo sysctl net.ipv4.tcp_sack=0
echo "Launching client..."
cc=$1
link=$2
duration=${3:-30}  # Default video duration: 30 seconds
client_type=${4:-"wget"}  # Default client: wget

if [ "$client_type" == "chrome" ]; then
    echo "Using Chrome for video traffic..."
    
    # Create a temporary directory for Chrome
    temp_dir="/tmp/chrome_data"
    mkdir -p "$temp_dir"
    log_file="$temp_dir/chrome_netlog.json"
    
    # Launch Chrome for video
    echo "Launching Chrome with URL: $link"
    echo "Network log will be saved to: $log_file"
    
    google-chrome --headless --no-sandbox --disable-gpu \
      --autoplay-policy=no-user-gesture-required \
      --log-net-log="$log_file" \
      --net-log-capture-mode=IncludeCookiesAndCredentials \
      --user-data-dir="$temp_dir" \
      "$link" &
    
    chrome_pid=$!
    
    # Let Chrome run for the specified duration
    echo "Capturing video traffic for $duration seconds..."
    sleep $duration
    
    # Kill Chrome
    echo "Stopping Chrome..."
    kill $chrome_pid
    wait $chrome_pid 2>/dev/null
    
    # Wait for log file to be written
    sleep 3
    
    # Check if network log exists
    if [ -f "$log_file" ]; then
        echo "Network log captured successfully"
        # Copy the network log to current directory
        cp "$log_file" ./chrome_netlog.json
        echo "Copied network log to ./chrome_netlog.json"
    else
        echo "ERROR: Network log not found at $log_file"
        # Create an empty log file to prevent errors
        echo "{\"events\":[]}" > ./chrome_netlog.json
        echo "Created empty network log"
    fi
    
    # Don't clean up temp_dir immediately to allow for debugging
    # rm -rf "$temp_dir"
    echo "Temporary Chrome data is in $temp_dir"
else
    # Original wget functionality
    echo $link
    wget --tries=1 --timeout=30 -U Mozilla $link -O index
fi

sleep 1
echo "DONE!"
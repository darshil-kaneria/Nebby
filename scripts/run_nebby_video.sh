#!/bin/bash
# port_based_bottlenecks.sh - Create separate bottlenecks for each port

# Usage: ./port_based_bottlenecks.sh <video_url> <cc_algorithm>
# Example: ./port_based_bottlenecks.sh https://www.youtube.com/watch?v=dQw4w9WgXcQ cubic

video_url=$1
cc_algorithm=${2:-"cubic"}  # Default: cubic

# Network parameters
predelay=2
postdelay=50
linkspeed=200
buffsize=2
duration=30

if [ -z "$video_url" ]; then
    echo "Usage: ./port_based_bottlenecks.sh <video_url> [cc_algorithm]"
    exit 1
fi

# Create a unique run ID
run_id="$cc_algorithm-$(date +%s)"
output_dir="../measurements/$run_id"
mkdir -p "$output_dir"
temp_dir="/tmp/nebby_$run_id"
mkdir -p "$temp_dir"

echo "===== Video Traffic Analysis with Per-Port Bottlenecks ====="
echo "Video URL: $video_url"
echo "CC Algorithm: $cc_algorithm"
echo "Network parameters: $predelay ms pre-delay, $postdelay ms post-delay, $linkspeed kbps"
echo "Output directory: $output_dir"

# Clean up any previous runs
./clean.sh

# Set the congestion control algorithm
sudo sysctl -w net.ipv4.tcp_congestion_control=$cc_algorithm
echo "Using congestion control: $cc_algorithm"

# Create bandwidth trace file
trace_file="../traces/bw$linkspeed.trace"
if [ ! -f "$trace_file" ]; then
    echo "Creating bandwidth trace file..."
    num=$(($linkspeed/12))
    > $trace_file  # Create/clear the file
    for (( c=1; c<=$num; c++ )); do
        echo $(($(($c*1000))/$num)) >> "$trace_file"
    done
    echo "Created trace file with $num entries"
fi

# Calculate BDP
bdp=$(($(($(($predelay+$postdelay))*$linkspeed*$buffsize))/4))
echo "BDP: $bdp bytes"

# Step 1: Initial browser session to identify ports
echo -e "\n===== Initial browser session to identify ports ====="

# Start packet capture for initial session
sudo tcpdump -i any -w "$temp_dir/initial.pcap" port 80 or port 443 -c 200 &
tcpdump_pid=$!
sleep 1

# Launch Chrome for a short time to identify initial connections
echo "Starting Chrome briefly to identify ports..."
google-chrome --headless --no-sandbox --disable-gpu \
  --log-net-log="$temp_dir/initial_netlog.json" \
  --net-log-capture-mode=IncludeCookiesAndCredentials \
  --user-data-dir="$temp_dir/chrome_data" \
  --autoplay-policy=no-user-gesture-required \
  "$video_url" > "$temp_dir/chrome_pre.log" 2>&1 &
pre_chrome_pid=$!

# Wait for some connections to be established
sleep 8

# Stop the pre-capture phase
echo "Stopping pre-capture..."
kill -SIGTERM $pre_chrome_pid 2>/dev/null
sleep 2
if ps -p $pre_chrome_pid > /dev/null; then
    kill -SIGKILL $pre_chrome_pid 2>/dev/null
fi
sudo kill $tcpdump_pid 2>/dev/null
wait $pre_chrome_pid 2>/dev/null
wait $tcpdump_pid 2>/dev/null

# Extract ports from the initial capture
echo "Extracting ports from initial capture..."
tshark -r "$temp_dir/initial.pcap" -T fields -e tcp.dstport -e tcp.srcport | sort | uniq > "$temp_dir/ports.txt"

# Check if we got any ports
port_count=$(wc -l < "$temp_dir/ports.txt")
if [ "$port_count" -eq 0 ]; then
    echo "No ports detected in initial capture. Using default port ranges."
    # Use common HTTP/HTTPS ports
    echo "80 443" > "$temp_dir/ports.txt"
    port_count=1
fi

echo "Detected $port_count port combinations"

# Step 2: Create run script for Chrome with main capture
cat > "$temp_dir/run_chrome.sh" << 'EOF'
#!/bin/bash
video_url=$1
temp_dir=$2
output_dir=$3
duration=$4

echo "Launching Chrome to play video: $video_url"
echo "Duration: $duration seconds"

google-chrome --headless --no-sandbox --disable-gpu \
  --autoplay-policy=no-user-gesture-required \
  --log-net-log="$temp_dir/chrome_netlog.json" \
  --net-log-capture-mode=IncludeCookiesAndCredentials \
  --user-data-dir="$temp_dir/chrome_data_main" \
  "$video_url" > "$output_dir/chrome.log" 2>&1 &
chrome_pid=$!

# Let Chrome run for the specified duration
echo "Running Chrome for $duration seconds..."
sleep $duration

# Gracefully stop Chrome
echo "Stopping Chrome..."
kill -SIGTERM $chrome_pid
sleep 5
if ps -p $chrome_pid > /dev/null; then
    kill -SIGKILL $chrome_pid
fi

# Copy network log
if [ -f "$temp_dir/chrome_netlog.json" ]; then
    # Fix JSON if needed
    if ! python -m json.tool "$temp_dir/chrome_netlog.json" > /dev/null 2>&1; then
        echo "Fixing JSON..."
        sed -i -e '$s/,$//' -e '$a}' "$temp_dir/chrome_netlog.json"
    fi
    cp "$temp_dir/chrome_netlog.json" "$output_dir/chrome_netlog.json"
fi

echo "Chrome capture complete"
EOF
chmod +x "$temp_dir/run_chrome.sh"

# Step 3: Start separate bottlenecks for each detected port
echo -e "\n===== Starting separate bottlenecks for each port ====="

# Create a coordination script to run multiple bottlenecks
cat > "$temp_dir/multi_bottleneck.sh" << 'EOF'
#!/bin/bash
trace_file=$1
bdp=$2
predelay=$3
postdelay=$4
chrome_script=$5
video_url=$6
temp_dir=$7
output_dir=$8
duration=$9
ports_file="${10}"

# Read ports file
readarray -t port_lines < "$ports_file"

# Create a directory for each port bottleneck
mkdir -p "$output_dir/bottlenecks"

# Start tcpdump to capture all traffic
sudo tcpdump -i any -w "$output_dir/all_traffic.pcap" port 80 or port 443 &
tcpdump_pid=$!
echo "$tcpdump_pid" > "$temp_dir/tcpdump_pid"

# Launch a bottleneck for each port
for i in "${!port_lines[@]}"; do
    ports=${port_lines[$i]}
    flow_id="flow_$i"
    mkdir -p "$output_dir/bottlenecks/$flow_id"
    
    # Extract the two ports
    port1=$(echo $ports | awk '{print $1}')
    port2=$(echo $ports | awk '{print $2}')
    
    echo "Starting bottleneck for $flow_id (ports: $port1, $port2)..."
    
    # Set up environment for this bottleneck
    # Use a unique log file and port
    mm_port=$((8000 + i))
    
    # Make sure these ports are not in use
    lsof -i :$mm_port > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        mm_port=$((mm_port + 100))  # Try a different port range
    fi
    
    # Start packet capture for these specific ports
    sudo tcpdump -i any -w "$output_dir/bottlenecks/$flow_id/traffic.pcap" \
        "tcp port $port1 or tcp port $port2" &
    echo "$! $flow_id tcpdump" >> "$temp_dir/pids"
    
    # Start mm-link with specified parameters
    # We use a named pipe to handle input/output
    mkfifo "$temp_dir/$flow_id.in" "$temp_dir/$flow_id.out"
    
    # Create the command for this specific bottleneck
    (
        mm-delay $predelay \
        mm-link $trace_file $trace_file \
        --uplink-queue=droptail --downlink-queue=droptail \
        --uplink-queue-args="bytes=$bdp" \
        --downlink-queue-args="bytes=$bdp" \
        --uplink-log="$output_dir/bottlenecks/$flow_id/uplink.log" \
        --downlink-log="$output_dir/bottlenecks/$flow_id/downlink.log" \
        mm-delay $postdelay \
        mm-server $mm_port > "$temp_dir/$flow_id.out" < "$temp_dir/$flow_id.in" &
        
        echo "$! $flow_id mm-link" >> "$temp_dir/pids"
    ) &
done

# Start the main Chrome session
echo "Starting main Chrome session..."
"$chrome_script" "$video_url" "$temp_dir" "$output_dir" "$duration"

# Wait for Chrome to complete
echo "Chrome session complete, cleaning up..."

# Kill all bottleneck processes
if [ -f "$temp_dir/pids" ]; then
    while read line; do
        pid=$(echo $line | awk '{print $1}')
        flow_id=$(echo $line | awk '{print $2}')
        type=$(echo $line | awk '{print $3}')
        
        echo "Stopping $type for $flow_id (PID: $pid)..."
        if [ "$type" = "tcpdump" ]; then
            sudo kill -SIGTERM $pid 2>/dev/null
        else
            kill -SIGTERM $pid 2>/dev/null
        fi
    done < "$temp_dir/pids"
fi

# Kill main tcpdump
if [ -f "$temp_dir/tcpdump_pid" ]; then
    sudo kill -SIGTERM $(cat "$temp_dir/tcpdump_pid") 2>/dev/null
fi

# Clean up named pipes
for i in "${!port_lines[@]}"; do
    flow_id="flow_$i"
    rm -f "$temp_dir/$flow_id.in" "$temp_dir/$flow_id.out"
done

echo "All bottlenecks stopped"
EOF
chmod +x "$temp_dir/multi_bottleneck.sh"

# Run the multi-bottleneck script
echo "Starting multi-bottleneck capture..."
"$temp_dir/multi_bottleneck.sh" \
    "$trace_file" "$bdp" "$predelay" "$postdelay" \
    "$temp_dir/run_chrome.sh" "$video_url" "$temp_dir" "$output_dir" "$duration" \
    "$temp_dir/ports.txt"

# Check if packet capture succeeded
if [ -f "$output_dir/all_traffic.pcap" ]; then
    pcap_size=$(du -h "$output_dir/all_traffic.pcap" | cut -f1)
    echo "Packet capture successful: $pcap_size"
    
    # Convert PCAP to CSV
    echo "Converting PCAP to CSV..."
    ../analysis/pcap2csv.sh "$output_dir/all_traffic.pcap"
    cp "$output_dir/all_traffic.pcap-tcp.csv" "$output_dir/$run_id-tcp.csv"
    
    # Also process individual flow captures
    echo "Processing individual flow captures..."
    for flow_dir in "$output_dir/bottlenecks/flow_"*; do
        if [ -d "$flow_dir" ]; then
            flow_id=$(basename "$flow_dir")
            pcap_file="$flow_dir/traffic.pcap"
            
            if [ -f "$pcap_file" ]; then
                ../analysis/pcap2csv.sh "$pcap_file"
                cp "$pcap_file-tcp.csv" "$output_dir/${flow_id}-tcp.csv"
            fi
        fi
    done
else
    echo "WARNING: Main packet capture not found"
    # Check if we have any individual flow captures
    for flow_dir in "$output_dir/bottlenecks/flow_"*; do
        if [ -d "$flow_dir" ]; then
            flow_id=$(basename "$flow_dir")
            pcap_file="$flow_dir/traffic.pcap"
            
            if [ -f "$pcap_file" ]; then
                echo "Found flow capture for $flow_id"
                ../analysis/pcap2csv.sh "$pcap_file"
                cp "$pcap_file-tcp.csv" "$output_dir/${flow_id}-tcp.csv"
                
                # If we don't have a main TCP file, use the first flow as main
                if [ ! -f "$output_dir/$run_id-tcp.csv" ]; then
                    cp "$pcap_file-tcp.csv" "$output_dir/$run_id-tcp.csv"
                fi
            fi
        fi
    done
    
    if [ ! -f "$output_dir/$run_id-tcp.csv" ]; then
        echo "ERROR: No packet captures found"
        exit 1
    fi
fi

# Analyze the results
echo -e "\n===== Analyzing results ====="

# Go to analysis directory
cd ../analysis

# Process network log to identify flow types
echo "Processing network log..."
if [ -f "$output_dir/chrome_netlog.json" ]; then
    python process_video_flows.py "$output_dir/chrome_netlog.json" "$output_dir/$run_id-tcp.csv"
else
    echo "WARNING: Chrome network log not found"
fi

# Run BiF analysis for main file
echo "Running BiF analysis for all traffic..."
python bif_lakshay.py "$run_id"

# Process each flow separately
echo "Processing individual flows..."
for flow_csv in "$output_dir/flow_"*"-tcp.csv"; do
    if [ -f "$flow_csv" ]; then
        flow_id=$(basename "$flow_csv" | sed 's/-tcp.csv//')
        echo "Analyzing flow: $flow_id"
        python bif_lakshay.py "$flow_id"
    fi
done

# Identify video flows
flow_types_file="$output_dir/$run_id-flow-types.json"
if [ -f "$flow_types_file" ]; then
    # Use Python to find video ports
    video_ports=$(python -c "
import json
import sys
try:
    with open('$flow_types_file') as f:
        data = json.load(f)
        for port, info in data.items():
            if info.get('type') == 'video':
                print(port)
except Exception as e:
    print(f'# Error: {e}', file=sys.stderr)
    ")
    
    if [ -n "$video_ports" ]; then
        echo "Found video flows on ports: $video_ports"
        
        # Analyze video flows
        for port in $video_ports; do
            echo "Analyzing video flow on port $port..."
            python features_lakshay.py "$run_id" "$port"
        done
    else
        echo "No video flows found, analyzing all flows..."
        
        # Analyze each flow separately
        for flow_csv in "$output_dir/flow_"*"-tcp.csv"; do
            if [ -f "$flow_csv" ]; then
                flow_id=$(basename "$flow_csv" | sed 's/-tcp.csv//')
                echo "Extracting features for flow: $flow_id"
                python features_lakshay.py "$flow_id"
            fi
        done
    fi
else
    echo "No flow types file found, analyzing all flows..."
    
    # Analyze each flow separately
    for flow_csv in "$output_dir/flow_"*"-tcp.csv"; do
        if [ -f "$flow_csv" ]; then
            flow_id=$(basename "$flow_csv" | sed 's/-tcp.csv//')
            echo "Extracting features for flow: $flow_id"
            python features_lakshay.py "$flow_id"
        fi
    done
fi

# Summarize results
echo -e "\n===== Experiment Summary ====="
echo "Video URL: $video_url"
echo "CC Algorithm: $cc_algorithm"
echo "Network parameters: $predelay ms pre-delay, $postdelay ms post-delay, $linkspeed kbps"
echo "Results location: $output_dir"

# Show CCA classification results
echo -e "\nCCA Classification Results:"
for cca_file in $(find "$output_dir" -name "*-cca.txt"); do
    flow_id=$(basename $cca_file | sed 's/-cca.txt//')
    echo "$flow_id: $(cat $cca_file)"
done

echo "===== Experiment Complete ====="
#!/bin/bash
# nebby-train.sh - Complete script for training the Nebby classifier
# Prerequisites: Docker containers with different CCAs must be running (from host-network-cca-servers.sh)

echo "======= NEBBY TRAINING SCRIPT ======="
echo "Starting training process for Nebby CCA classifier"

# Create necessary directories
mkdir -p measurements
mkdir -p candidates-measurements
mkdir -p logs/results
mkdir -p logs/plots

# Function to check and optionally change host CCA
check_host_cca() {
    local target_cca="$1"
    current_cca=$(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')
    echo "Current host CCA: $current_cca"
    
    if [ -n "$target_cca" ] && [ "$current_cca" != "$target_cca" ]; then
        echo "Changing host CCA from $current_cca to $target_cca"
        sudo sysctl net.ipv4.tcp_congestion_control="$target_cca"
        
        # Verify the change
        new_cca=$(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')
        if [ "$new_cca" = "$target_cca" ]; then
            echo "✅ Host CCA successfully changed to $target_cca"
        else
            echo "❌ Failed to change host CCA to $target_cca"
            return 1
        fi
    fi
    return 0
}

# Check for containers
CONTAINERS=$(sudo docker ps --format '{{.Names}}' | grep "^nebby-")
if [ -z "$CONTAINERS" ]; then
    echo "Error: No nebby CCA containers found. Please run host-network-cca-servers.sh first."
    exit 1
fi

progress() {
    echo ""
    echo "===== STEP $1: $2 ====="
}

# Display current host CCA
echo "Host system CCA configuration:"
check_host_cca

# Step 1: Collect BiF Traces
progress "1" "Collecting BiF Traces"

# Get list of CCA names and URLs
declare -a CCA_NAMES=()
declare -a CCA_URLS=()

for container in $CONTAINERS; do
    CCA=${container#nebby-}
    CCA_NAMES+=("$CCA")
    # Use sudo only for Docker command
    PORT=$(sudo docker exec $container env | grep PORT | cut -d= -f2)
    CCA_URLS+=("http://172.26.46.4:$PORT/test-400kb.bin")
    echo "Found server: $CCA on port $PORT"
done

# Create a configuration file for wget
CONFIG_FILE="nebby-training-urls.txt"
> $CONFIG_FILE

for i in "${!CCA_NAMES[@]}"; do
    echo "${CCA_URLS[$i]} ${CCA_NAMES[$i]}" >> $CONFIG_FILE
    echo "Added ${CCA_NAMES[$i]} to training set"
done

# Function to run tests for a CCA (ensuring no sudo for mm commands)
run_cca_test() {
    local cca_name="$1"
    local url="$2"
    local delay_suffix="$3"
    local delay_ms="$4"
    
    echo "Collecting BiF traces for $cca_name$delay_suffix using $url"
    
    # Optional: Change host CCA to match the one being tested
    # Uncomment if you want to align host CCA with container CCA
    check_host_cca "$cca_name"
    
    # Use Nebby's run_test.sh script (this should handle mm commands without sudo)
    cd scripts
    ./run_test.sh "$cca_name$delay_suffix" 5 $delay_ms 200 2 "$url"
    cd ..
    
    echo "✅ Collected traces for $cca_name$delay_suffix"
}

# Collect traces using wget for all CCAs
for i in "${!CCA_NAMES[@]}"; do
    CCA="${CCA_NAMES[$i]}"
    URL="${CCA_URLS[$i]}"
    
    # Standard collection (50ms delay)
    run_cca_test "$CCA" "$URL" "" 50
    
    # Additional collection with different delay profile (100ms) as mentioned in the paper
    run_cca_test "$CCA" "$URL" "-100ms" 100
done

# Store original host CCA to restore later if needed
ORIGINAL_CCA=$(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')

# Step 2: Processing BiF Traces
progress "2" "Processing BiF Traces"
cd analysis
python3 run-lakshay.py -b "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

# Step 3: Feature extraction
progress "3" "Extracting Features from Traces"
cd analysis
python3 run-lakshay.py -f "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

# Step 4: Polynomial fit
progress "4" "Fitting Polynomials to Features"
cd analysis
python3 run-lakshay.py -c "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

# Step 5: Final training step
progress "5" "Training Classification Model"
MODEL_FILE="nebby_model_$(date +%Y%m%d_%H%M%S).pkl"
cd analysis
python3 run-lakshay.py -t "../$MODEL_FILE" "../measurements/"
cd ..

# Step 6: Model validation
progress "6" "Testing Model Accuracy"
cd analysis
python3 run-lakshay.py -a "../$MODEL_FILE" "../measurements/"
cd ..

# Restore original CCA if it was changed
if [ "$ORIGINAL_CCA" != "$(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')" ]; then
    echo "Restoring original host CCA: $ORIGINAL_CCA"
    check_host_cca "$ORIGINAL_CCA"
fi

echo ""
echo "🎉 TRAINING COMPLETE 🎉"
echo "Model saved to: $MODEL_FILE"
echo ""
echo "Training Summary:"
echo "- CCAs trained: ${CCA_NAMES[*]}"
echo "- Delay profiles: 50ms, 100ms"
echo "- Host CCA: $(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')"
echo ""
echo "To use the trained model for identification, run:"
echo "cd analysis"
echo "python3 run-lakshay.py -a \"../$MODEL_FILE\" <target_directory>"
echo ""
echo "🚀 You can now use Nebby to identify CCAs on the Internet!"

# Additional notes for testing new CCAs
echo ""
echo "📝 Notes for testing new CCAs:"
echo "- Remember to change host CCA using: sudo sysctl net.ipv4.tcp_congestion_control=<cca_name>"
echo "- Do NOT run mm commands with sudo"
echo "- Ensure the run_test.sh script handles mm commands with appropriate user permissions"
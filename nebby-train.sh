#!/bin/bash
# nebby-train.sh - Complete script for training the Nebby classifier
# Modified to capture 10 traces per CCA

echo "======= NEBBY TRAINING SCRIPT (10 TRACES PER CCA) ======="
echo "Starting training process for Nebby CCA classifier"

# Create necessary directories
mkdir -p measurements
mkdir -p candidates-measurements
mkdir -p logs/results
mkdir -p logs/plots

# Number of traces to collect per CCA
NUM_TRACES=20

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
    echo "Error: No nebby CCA containers found. Please run local_sv/setup_cca.sh first."
    exit 1
fi

progress() {
    echo ""
    echo "===== STEP $1: $2 ====="
}

# Display current host CCA
echo "Host system CCA configuration:"
check_host_cca

# Step 1: Collect BiF Traces (10 per CCA)
# progress "1" "Collecting BiF Traces (${NUM_TRACES} per CCA)"

# # Get list of CCA names and URLs
# declare -a CCA_NAMES=()
# declare -a CCA_URLS=()

# for container in $CONTAINERS; do
#     CCA=${container#nebby-}
#     CCA_NAMES+=("$CCA")
#     # Use sudo only for Docker command
#     PORT=$(sudo docker exec $container env | grep PORT | cut -d= -f2)
#     CCA_URLS+=("http://192.168.0.5:$PORT/test-400kb.bin")
#     echo "Found server: $CCA on port $PORT"
# done

# # Function to run tests for a CCA with multiple traces
# run_cca_test() {
#     local cca_name="$1"
#     local url="$2"
#     local delay_suffix="$3"
#     local delay_ms="$4"
#     local trace_num="$5"
    
#     echo "Collecting BiF trace ${trace_num}/${NUM_TRACES} for $cca_name$delay_suffix using $url"
    
#     # Optional: Change host CCA to match the one being tested
#     # Uncomment if you want to align host CCA with container CCA
#     check_host_cca "$cca_name"
    
#     # Create unique filename for this trace
#     local trace_id="${cca_name}${delay_suffix}-v${trace_num}"
    
#     # Use Nebby's run_test.sh script
#     cd scripts
#     ./run_test.sh "$trace_id" 5 $delay_ms 200 2 "$url"
#     cd ..
    
#     echo "✅ Collected trace ${trace_num} for $cca_name$delay_suffix"
# }

# # Collect multiple traces for each CCA
# for i in "${!CCA_NAMES[@]}"; do
#     CCA="${CCA_NAMES[$i]}"
#     URL="${CCA_URLS[$i]}"
    
#     echo ""
#     echo "🔄 Collecting traces for $CCA..."
    
#     # Collect NUM_TRACES for standard delay profile (50ms)
#     for trace_num in $(seq 1 $NUM_TRACES); do
#         run_cca_test "$CCA" "$URL" "" 50 "$trace_num"
#         sleep 2  # Brief pause between measurements
#     done
    
#     # Collect NUM_TRACES for higher delay profile (100ms)
#     for trace_num in $(seq 1 $NUM_TRACES); do
#         run_cca_test "$CCA" "$URL" "-100ms" 100 "$trace_num"
#         sleep 2  # Brief pause between measurements
#     done
    
#     echo "✅ Completed all ${NUM_TRACES} traces for $CCA (both delay profiles)"
# done

# Store original host CCA to restore later if needed
ORIGINAL_CCA=$(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')

# Step 2: Processing BiF Traces
progress "2" "Processing BiF Traces"
cd analysis

# Build list of all trace files for processing
ALL_TRACES=()
for cca in "${CCA_NAMES[@]}"; do
    for trace_num in $(seq 1 $NUM_TRACES); do
        ALL_TRACES+=("${cca}-v${trace_num}")
        ALL_TRACES+=("${cca}-100ms-v${trace_num}")
    done
done

python3 run-lakshay.py -b "${ALL_TRACES[@]}"
cd ..

# Step 3: Feature extraction
progress "3" "Extracting Features from Traces"
cd analysis
python3 run-lakshay.py -f "${ALL_TRACES[@]}"
cd ..

# Step 4: Polynomial fit
progress "4" "Fitting Polynomials to Features"
cd analysis
python3 run-lakshay.py -c "${ALL_TRACES[@]}"
cd ..

# Step 5: Final training step
progress "5" "Training Classification Model"
MODEL_FILE="nebby_model_$(date +%Y%m%d_%H%M%S)_${NUM_TRACES}traces.pkl"
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
echo "- Traces per CCA: $NUM_TRACES per delay profile"
echo "- Total traces: $((${#CCA_NAMES[@]} * NUM_TRACES * 2))"
echo "- Delay profiles: 50ms, 100ms"
echo "- Host CCA: $(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2 | tr -d ' ')"
echo ""
echo "To use the trained model for identification, run:"
echo "cd analysis"
echo "python3 run-lakshay.py -a \"../$MODEL_FILE\" <target_directory>"
echo ""
echo "🚀 You can now use Nebby to identify CCAs on the Internet!"
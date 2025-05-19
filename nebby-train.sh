#!/bin/bash

# nebby-train.sh - Complete script for training the Nebby classifier
# Prerequisites: Docker containers with different CCAs must be running (from host-network-cca-servers.sh)

echo "======= NEBBY TRAINING SCRIPT ======="
echo "Starting training process for Nebby CCA classifier"

# Step 0: Create directories if they don't exist
mkdir -p measurements
mkdir -p candidates-measurements
mkdir -p logs/results
mkdir -p logs/plots

# Get list of running CCA servers (using sudo only for Docker)
CONTAINERS=$(sudo docker ps --format '{{.Names}}' | grep "^nebby-")
if [ -z "$CONTAINERS" ]; then
  echo "Error: No nebby CCA containers found. Please run host-network-cca-servers.sh first."
  exit 1
fi

# Function to display progress
progress() {
  echo ""
  echo "===== STEP $1: $2 ====="
}

# Step 1: Collect BiF Traces
# progress "1" "Collecting BiF Traces"

# # Get list of CCA names and URLs
# declare -a CCA_NAMES=()
# declare -a CCA_URLS=()

# for container in $CONTAINERS; do
#   CCA=${container#nebby-}
#   CCA_NAMES+=("$CCA")
  
#   # Use sudo only for Docker command
#   PORT=$(sudo docker exec $container env | grep PORT | cut -d= -f2)
#   CCA_URLS+=("http://10.50.221.166:$PORT/test-400kb.bin")
  
#   echo "Found server: $CCA on port $PORT"
# done

# # Create a configuration file for wget
# CONFIG_FILE="nebby-training-urls.txt"
# > $CONFIG_FILE

# for i in "${!CCA_NAMES[@]}"; do
#   echo "${CCA_URLS[$i]} ${CCA_NAMES[$i]}" >> $CONFIG_FILE
#   echo "Added ${CCA_NAMES[$i]} to training set"
# done

# # Collect traces using wget for all CCAs
# for i in "${!CCA_NAMES[@]}"; do
#   CCA="${CCA_NAMES[$i]}"
#   URL="${CCA_URLS[$i]}"
  
#   echo "Collecting BiF traces for $CCA using $URL"
  
#   # Use Nebby's run_test.sh script
#   cd scripts
#   ./run_test.sh "$CCA" 5 50 200 2 "$URL"
#   cd ..
  
#   # Additional collection with different delay profile (100ms) as mentioned in the paper
#   cd scripts
#   ./run_test.sh "${CCA}-100ms" 5 100 200 2 "$URL"
#   cd ..
  
#   echo "✅ Collected traces for $CCA"
# done

# Running bif analysis
progress "2" "Processing BiF Traces"
cd analysis
python3 run-lakshay.py -b "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

progress "3" "Extracting Features from Traces"
cd analysis
python3 run-lakshay.py -f "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

# Polynomial fit
progress "4" "Fitting Polynomials to Features"
cd analysis
python3 run-lakshay.py -c "${CCA_NAMES[@]}" "${CCA_NAMES[@]/%/-100ms}"
cd ..

# FInal training step
progress "5" "Training Classification Model"
MODEL_FILE="nebby_model_$(date +%Y%m%d).pkl"
cd analysis
python3 run-lakshay.py -t "../$MODEL_FILE" "../measurements/"
cd ..

progress "6" "Testing Model Accuracy"
cd analysis
python3 run-lakshay.py -a "../$MODEL_FILE" "../measurements/"
cd ..

echo "Model saved to: $MODEL_FILE"
echo ""
echo "To use the trained model for identification, run:"
echo "cd analysis"
echo "python3 run-lakshay.py -a \"../$MODEL_FILE\" <target_directory>"
echo ""
echo "You can now use Nebby to identify CCAs on the Internet!"
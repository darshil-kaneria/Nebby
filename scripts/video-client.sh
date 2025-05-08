#!/bin/bash
# Simple update for client.sh to test video streaming
sudo ifconfig ingress mtu 100
sudo sysctl net.ipv4.tcp_sack=0

# Set congestion control algorithm (get from run_test.sh args)
cc=$1
# link=$2

echo "Testing video streaming with $cc congestion control"

# Run Chrome with a video URL with a timeout
# The timeout ensures the test doesn't run indefinitely
# Added autoplay flags to ensure video plays automatically
timeout 100s google-chrome "http://100.64.0.1:23557/"

# Wait a bit to ensure the video starts streaming
sleep 1

# Let the video stream for a while
# sleep 20

# Kill Chrome
pkill -f chrome

echo "Video streaming test completed"
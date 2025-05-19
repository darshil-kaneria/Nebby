#!/bin/bash
sudo ifconfig ingress mtu 100
sudo sysctl net.ipv4.tcp_sack=0
echo "Launching client..."
cc=$1
link=$2

wget_out="nebby_wget_out.txt"

echo "Using congestion control: $cc" 
echo "Connecting to: $link"
echo "$cc" >> $wget_out
echo "$link" >> $wget_out

timeout 15s wget -U Mozilla --tries=1 --timeout=15 "$link" -O index &>> $wget_out

sleep 2

echo "Download complete!"
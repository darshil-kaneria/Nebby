#!/bin/bash
# Modified run_test.sh to support video traffic

cc=$1
predelay=$2
postdelay=$3
linkspeed=$4
buffsize=$5
file=$6
duration=${7:-30}  # Default video duration
client_type=${8:-"wget"}  # Default client type

./clean.sh

# Run the simulation with appropriate client type
./simnet.sh $cc $predelay $postdelay $linkspeed $buffsize $file $duration $client_type
../analysis/pcap2csv.sh test.pcap

# Copy results to measurements directory
cp test.pcap-tcp.csv ../measurements/$cc-tcp.csv
cp test.pcap-udp.csv ../measurements/$cc-udp.csv

# If Chrome was used, copy the network log
if [ "$client_type" == "chrome" ]; then
    cp chrome_netlog.json ../measurements/$cc-netlog.json
    
    # Process multiple flows if needed
    # Parse the chrome_netlog.json to identify different flows
    python3 ../analysis/process_video_flows.py ../measurements/$cc-netlog.json ../measurements/$cc-tcp.csv
fi

# Clean up
rm -f index*
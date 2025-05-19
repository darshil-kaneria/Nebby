#!/bin/bash
if [ $# -eq 0 ]
then
echo "This scripts converts .pcap files to a more parse-able .csv format." 
echo "To convert X.pcap to X.csv, run './pcap2csv.sh X' "
exit
fi

echo -e "[Converting recv data to .csv format]"

# Try a more robust tshark command with explicit field extraction
tshark -r $1 -T fields \
  -e frame.time_epoch \
  -e frame.time_relative \
  -e tcp.time_relative \
  -e frame.number \
  -e frame.len \
  -e ip.src \
  -e tcp.srcport \
  -e ip.dst \
  -e tcp.dstport \
  -e tcp.len \
  -e tcp.seq \
  -e tcp.ack \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -E occurrence=f > $1-tcp.csv

# Add verbose option to see if there are issues
echo "Debug info for TCP extraction:"
tshark -r $1 -T fields -e ip.proto -e tcp.srcport -E header=y -E separator=, | head

# For UDP traffic, use a display filter
tshark -r $1 -Y "udp" -T fields \
  -e frame.time_epoch \
  -e frame.time_relative \
  -e frame.number \
  -e frame.len \
  -e ip.src \
  -e udp.srcport \
  -e ip.dst \
  -e udp.dstport \
  -e udp.length \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -E occurrence=f > $1-udp.csv

# Show statistics about the capture file
echo "Capture file statistics:"
capinfos $1
#!/bin/bash
# Modified simnet.sh to support video traffic

cc=$1
predelay=$2
postdelay=$3
bw=$4
buffBDP=$5
link=$6
duration=${7:-30}  # Default video duration
client_type=${8:-"wget"}  # Default client type

# Calculate BDP and buffer size
bdp=$(($(($(($predelay+$postdelay))*$bw*$buffBDP))/4))
echo "BDP: $bdp"
buff=$bdp
echo "Buffer size: $buff"

# Buffer AQM
aqm=droptail

# Create bandwidth trace file
num=$(($bw/12))
rm -f ../traces/bw.trace
touch ../traces/bw.trace
for (( c=1; c<=$num; c++ ))
do
  echo $(($(($c*1000))/$num)) >> ../traces/bw.trace
done

# Pcap name
dump=test.pcap
echo "CC: $cc"
echo "Pre-delay: $predelay"

# Pass client type parameter to btl.sh
mm-delay $predelay ./btl.sh $dump $postdelay $buff $aqm $cc $link $duration $client_type

# Cleanup
sudo killall mm-delay
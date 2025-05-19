#!/bin/bash
cc=$1
#pre delay in ms
predelay=$2
# post delay in ms
postdelay=$3
# btl bandwidth in kbps
bw=$4
# Buffer size in bytes, set to 1 BDP
buffBDP=$5
link=$6
bdp=$(($(($(($predelay+$postdelay))*$bw*$buffBDP))/4))
echo $bdp
buff=$bdp
echo $buff
# buffer AQM
aqm=droptail

num=$(($bw/12))
rm -f ../traces/bw.trace
touch ../traces/bw.trace
for (( c=1; c<=$num; c++ ))
do
echo $(($(($c*1000))/$num)) >> ../traces/bw.trace
done
#pcap name
echo $cc
dump=test.pcap
echo $predelay
# If running from scripts directory
if [ -f "btl.sh" ]; then
  mm-delay $predelay ./btl.sh $dump $postdelay $buff $aqm $cc $link
  echo "mm-delay $predelay ./btl.sh $dump $postdelay $buff $aqm $cc $link"
else
  # If running from another directory
  mm-delay $predelay ./scripts/btl.sh $dump $postdelay $buff $aqm $cc $link
  echo "mm-delay $predelay ./scripts/btl.sh $dump $postdelay $buff $aqm $cc $link"
fi
sudo killall mm-delay

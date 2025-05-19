cc=$1
predelay=$2
postdelay=$3
linkspeed=$4
buffsize=$5
file=$6

./clean.sh

#sudo echo "0" > /proc/sys/net/ipv4/tcp_sack
echo "Running Simnet"
./simnet.sh $cc $predelay $postdelay $linkspeed $buffsize $file
echo "Running pcap2csv"
../analysis/pcap2csv.sh test.pcap

cp test.pcap-tcp.csv ../measurements/$cc-tcp.csv
cp test.pcap-udp.csv ../measurements/$cc-udp.csv

rm -f index*

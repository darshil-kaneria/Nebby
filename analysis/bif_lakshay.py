''' 
This is the file that has the code to generate the bytes-in-flight(bif) trace for a connection.
'''

import csv
import matplotlib.pyplot as plt
import sys

SHOW=False
MULTI_GRAPH=False
SMOOTHENING=False
ONLY_STATS=False
s_factor=0.9

PATH="../measurements/"

PKT_SIZE = 88

yellow = '\033[93m'
green = '\033[92m'
red = '\033[91m'
blue = '\033[94m'
pink = '\033[95m'
black = '\033[90m'

'''
TODO: 
o Add functionality where you only plot flows that send more than x bytes of data
o Sort stats and graphs by flow size
o Organize plots by flow size (larger flows have larger graphs)
o Custom smoothening function
'''

fields=["frame.time_epoch", "frame.time_relative", "tcp.time_relative", "frame.number", "frame.len", "ip.src", "tcp.srcport", "ip.dst", "tcp.dstport", "tcp.len", "tcp.seq", "tcp.ack"]

class pkt:
    contents=[]
    def __init__(self, fields) -> None:
        self.contents=[]
        for f in fields:
            self.contents.append(f)

    def get(self, field):
        return self.contents[fields.index(field)]
        

def process_flows(cc, dir, p="y"):
    name = dir + cc + "-tcp.csv"
    with open(name) as csv_file:
        print("Reading " + name + "...")
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        total_bytes = 0
        '''
        Flow tracking:
        o Identify all packets that are either sourced from or headed to the client
        o Group different flows by client's port
        '''
        flows = {}
        data_sent = 0
        # ACK and RTX measurement
        ooa = set()
        rp = set()
        ooaCount = 0
        rpCount = 0
        backAck = 0
        host_port = None
        
        for row in csv_reader:
            reTx = 0
            
            ooAck = 0
            dupAck = 0
            retPacket = 0
            
            packet = pkt(row)
            ackPkt = False
            validPkt = False
            if line_count == 0:
                # reject the header
                line_count += 1
                continue
            if data_sent == 0:
                # Look for client IP pattern (10.0.0.x)
                if packet.get("ip.src") and "10.0.0." in packet.get("ip.src"):
                    data_sent = 1
                    host_port = packet.get("ip.src")
                elif packet.get("ip.dst") and "10.0.0." in packet.get("ip.dst"):
                    data_sent = 1
                    host_port = packet.get("ip.dst")
                if data_sent == 0:
                    continue
            
            if packet.get("ip.src") == host_port and packet.get("frame.time_relative") != '' and packet.get("tcp.ack") != '': 
                # we care about this ACK packet
                validPkt = True
                ackPkt = True
                port = packet.get("tcp.srcport")
                
                if port not in flows:
                    flows[port] = {"OOA": [], "DA": [], "max_seq": 0, "loss_bif": 0, "max_ack": int(packet.get("tcp.ack") or 0), "serverip": packet.get("ip.dst"), "serverport": packet.get("tcp.dstport"), "act_times": [], "times": [], "windows": [], "cwnd": [], "bif": 0, "last_ack": 0, "last_seq": 0, "pif": 0, "drop": [], "next": 0, "retrans": []}
                else:
                    # check for Out of Order Ack (OOA)
                    ack_val = int(packet.get("tcp.ack") or 0)
                    if ack_val <= int(flows[port]["max_ack"]):
                        if ack_val == backAck:
                            dupAck = True
                            flows[port]["DA"].append(float(packet.get("frame.time_relative")))
                        else:
                            ooAck = True
                            flows[port]["OOA"].append(float(packet.get("frame.time_relative")))
                        backAck = ack_val
                    # update max_ack
                    flows[port]["max_ack"] = max(flows[port]["max_ack"], ack_val)
                    seq_val = int(packet.get("tcp.seq") or 0)
                    if seq_val < flows[port]["max_ack"]:
                        reTx += int(packet.get("tcp.len") or 0)
                    
            elif packet.get("ip.dst") == host_port and packet.get("frame.time_relative") != '' and packet.get("tcp.seq") != '':
                # we care about this Data packet
                validPkt = True
                port = packet.get("tcp.dstport")
                
                if port not in flows:
                    flows[port] = {"OOA": [], "DA": [], "max_seq": int(packet.get("tcp.seq") or 0), "loss_bif": 0, "max_ack": 0, "serverip": packet.get("ip.src"), "serverport": packet.get("tcp.srcport"), "act_times": [], "times": [], "windows": [], "cwnd": [], "bif": 0, "last_ack": 0, "last_seq": 0, "pif": 0, "drop": [], "next": 0, "retrans": []}
                
                else:
                    seq_val = int(packet.get("tcp.seq") or 0)
                    flows[port]["max_seq"] = max(flows[port]["max_seq"], seq_val)
                
                seq_val = int(packet.get("tcp.seq") or 0)
                if seq_val < flows[port]["max_seq"]:
                    retPacket = True
                    if len(flows[port]["times"]) > 0:
                        flows[port]["retrans"].append(flows[port]["times"][-1])
                    
            if validPkt == True:
                bif = 0
                normal_est_bif = int(flows[port]["max_seq"]) - int(flows[port]["max_ack"]) + PKT_SIZE
                loss_est_bif = flows[port]["loss_bif"]
                if ackPkt and dupAck and len(flows[port]["windows"]) > 10:
                    if dupAck:
                        # if we have received a duplicate ack then we need to reduce the bytes in flight by packet size
                        # we also increase max ack to correct for the consolidated ack being sent later
                        loss_est_bif = int(flows[port]["windows"][-1]) - PKT_SIZE
                        flows[port]["max_ack"] += PKT_SIZE
                        
                        bif = min(normal_est_bif, loss_est_bif)
                        if p == "y":
                            print(green + "Duplicate Ack", int(packet.get("tcp.ack") or 0), "Max Ack", flows[port]["max_ack"], "BIF", bif)
                        
                elif ackPkt:
                    loss_est_bif = normal_est_bif 
                    bif = normal_est_bif    
                    if ooAck:
                        ooaCount += 1
                        if p == "y":
                            print(red + "Out of Order Ack", int(packet.get("tcp.ack") or 0), "Max Ack", flows[port]["max_ack"], "BIF", normal_est_bif)
                        ooa.add(int(packet.get("tcp.ack") or 0))
                    else:
                        if p == "y":
                            print(black + "Inorder Ack", int(packet.get("tcp.ack") or 0), "Max Seq", flows[port]["max_seq"], "BIF", normal_est_bif)
                else:
                    bif = normal_est_bif
                    if retPacket == True:
                        rpCount += 1
                        rp.add(int(packet.get("tcp.seq") or 0))
                        if p == "y":
                            print(pink + "Retransmitted Packet", int(packet.get("tcp.seq") or 0), "Next", flows[port]["max_seq"] + PKT_SIZE, "BIF", bif)
                    else:
                        if p == "y":
                            print(blue + "Inorder Packet", int(packet.get("tcp.seq") or 0), "Next", flows[port]["max_seq"] + PKT_SIZE, "BIF", bif)
                flows[port]["loss_bif"] = loss_est_bif
                flows[port]["windows"].append(int(bif))
                flows[port]["times"].append(float(packet.get("frame.time_relative")))
            
            line_count += 1
            total_bytes += int(packet.get("frame.len") or 0)
            
        if p == "y":
            print("Out of Order Acks", len(ooa), "Retransmitted Packets", len(rp))
            print("Count Out of Order Acks", ooaCount, "Retransmitted Packets", rpCount)
            print("OOA", ooa, "RP", rp)
    return flows

def custom_smooth_function():
    pass

def get_flow_stats(flows):
    num = len(flows.keys())
    print("FLOW STATISTICS: \nNumber of flows: ", num)
    print("------------------------------------------------------------------------------")
    print('%6s' % "port", '%15s' % "SrcIP", '%8s' % "SrcPort", '%8s' % "duration", '%8s' % "start", '%8s' % "end", '%8s' % "Sent (B)", '%8s' % "Recv (B)",)
    for k in flows.keys():
        print('%6s' % k, '%15s' % flows[k]["serverip"], '%8s' % flows[k]["serverport"], '%8s' % str('%.2f' % (flows[k]["times"][-1] - flows[k]["times"][0])), '%8s' % str('%.2f' % flows[k]["times"][0]), '%8s' % str('%.2f' % flows[k]["times"][-1]), '%8s' % flows[k]["last_seq"], '%8s' % flows[k]["last_ack"])
    return num

def run(files, p):
    flows = {}
    from globals_lakshay import PATH
    for f in files:
        algo_cc = f
        # Get the data for all the flows
        print("==============================================================================")
        print("opening trace" + PATH + algo_cc + ".csv...")
        flow = process_flows(algo_cc, PATH, p=p)
        # decide on final graph layout
        num = get_flow_stats(flow)

        if ONLY_STATS:
            sys.exit()

        if num == 1:
            MULTI_GRAPH = False
        # grid size
        if MULTI_GRAPH:
            size = (0, 0)
            grids = {1: (2, 2), 2: (2, 2), 4: (2, 2), 6: (2, 3), 9: (3, 3), 12: (3, 4), 15: (3, 5), 16: (4, 4), 20: (5, 4), 24: (6, 4), 30: (6, 5), 36: (6, 6), 40: (8, 5), 42: (8, 7), 49: (7, 7)}
            g = num
            while g <= 49 and g not in grids:
                g += 1
            if g in grids.keys():
                size = grids[g]
            else:
                size = grids[49]  
            fig, axs = plt.subplots(size[0], size[1])
            for i in range(size[0]):
                for j in range(size[1]):
                    if i == size[0] - 1:
                        axs[i][j].set_xlabel("Time (s)")
                    if j == 0:
                        axs[i][j].set_ylabel("Bytes in flight")
        else:
            plt.xlabel("Time (s)")
            plt.ylabel("Bytes in flight")
        counter = 0
        for port in flows.keys():
            if MULTI_GRAPH:  
                axs[counter % size[0]][(counter // size[0]) % size[1]].scatter(flows[port]["times"], flows[port]["windows"], color="#858585")
                axs[counter % size[0]][(counter // size[0]) % size[1]].plot(flows[port]["times"], flows[port]["windows"], label=str(port), linestyle="solid")
            else:
                plt.plot(flows[port]["times"], flows[port]["windows"], label=str(port), linestyle="solid")
                plt.scatter(flows[port]["times"], flows[port]["windows"], color="#858585")
            counter += 1
        if MULTI_GRAPH:
            counter = 0
            for port in flows.keys():
                axs[counter % size[0]][(counter // size[0]) % size[1]].legend()
                counter += 1
        else:
            plt.legend()
        if MULTI_GRAPH:
            fig.set_size_inches(16, 12)
        if SHOW:
            plt.show()
        else:
            plt.savefig("../logs/results/" + algo_cc + ".png", dpi=600, bbox_inches='tight', pad_inches=0)
        flows[f] = flow
    return flows
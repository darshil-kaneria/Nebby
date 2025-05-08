import csv
import matplotlib.pyplot as plt
import sys
import math

SHOW=True
MULTI_GRAPH=False
SMOOTHENING=False
ONLY_STATS=False
s_factor=0.9

fields=["time", "frame_time_rel", "tcp_time_rel", "frame_num", "frame_len", "ip_src", "src_port", "ip_dest", "dest_port", "tcp_len", "seq", "ack"]

class pkt:
    contents=[]
    def __init__(self, fields) -> None:
        self.contents=[]
        for f in fields:
            self.contents.append(f)

    def get(self, field):
        if fields.index(field) < len(self.contents):
            return self.contents[fields.index(field)]
        return ""  # Return empty string for missing fields

def process_flows(cc, dir):
    with open(dir+cc+"-tcp.csv") as csv_file:
        print("Reading "+dir+cc+"-tcp.csv...")
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        total_bytes=0
        
        flows={}
        data_sent = 0
        host_port = None
        host_ip = None
        
        # First pass - determine the host IP (could be 10.0.0.x or 100.64.0.x)
        ip_counts = {}
        for row in csv_reader:
            if line_count == 0:  # Skip header
                line_count += 1
                continue
                
            packet = pkt(row)
            src_ip = packet.get("ip_src")
            if src_ip and (src_ip.startswith("10.0.0.") or src_ip.startswith("100.64.0.")):
                ip_counts[src_ip] = ip_counts.get(src_ip, 0) + 1
                
        # Reset file pointer
        csv_file.seek(0)
        line_count = 0
        
        # Determine most common local IP
        if ip_counts:
            host_ip = max(ip_counts, key=ip_counts.get)
            print(f"Detected host IP: {host_ip}")
        else:
            print("Warning: No local IPs detected in the trace!")
            return {}
            
        # Second pass - process packets
        for row in csv_reader:
            packet = pkt(row)
            validPkt = False
            
            if line_count == 0:  # Skip header
                line_count += 1
                continue
                
            # Skip packets without proper TCP data
            if not packet.get("seq") or not packet.get("ack") or not packet.get("tcp_len"):
                line_count += 1
                continue
                
            # Process ACK packets from host
            if packet.get("ip_src") == host_ip and packet.get("frame_time_rel") and packet.get("ack"):
                try:
                    validPkt = True
                    port = packet.get("src_port") or "default"
                    
                    if port not in flows:
                        flows[port] = {
                            "serverip": packet.get("ip_dest"), 
                            "serverport": packet.get("dest_port"), 
                            "times": [], "windows": [], "cwnd": [], 
                            "bif": 0, "last_ack": 0, "last_seq": 0, "pif": 0
                        }
                        
                    flows[port]["times"].append(float(packet.get("frame_time_rel")))
                    
                    # Safely handle ACK calculations
                    current_ack = int(packet.get("ack") or 0)
                    flows[port]["bif"] -= (current_ack - flows[port]["last_ack"])
                    flows[port]["last_ack"] = current_ack
                    
                    flows[port]["pif"] -= 1
                    flows[port]["cwnd"].append(flows[port]["pif"])
                except (ValueError, TypeError) as e:
                    print(f"Error processing ACK packet: {e}")
                    
            # Process data packets to host
            elif packet.get("ip_dest") == host_ip and packet.get("frame_time_rel") and packet.get("seq"):
                try:
                    validPkt = True
                    port = packet.get("dest_port") or "default"
                    
                    if port not in flows:
                        flows[port] = {
                            "serverip": packet.get("ip_src"), 
                            "serverport": packet.get("src_port"), 
                            "times": [], "windows": [], "cwnd": [], 
                            "bif": 0, "last_ack": 0, "last_seq": 0, "pif": 0
                        }
                        
                    flows[port]["times"].append(float(packet.get("frame_time_rel")))
                    
                    # Safely handle SEQ calculations
                    current_seq = int(packet.get("seq") or 0)
                    flows[port]["bif"] += (current_seq - flows[port]["last_seq"])
                    flows[port]["last_seq"] = current_seq
                    
                    flows[port]["pif"] += 1
                    flows[port]["cwnd"].append(flows[port]["pif"])
                except (ValueError, TypeError) as e:
                    print(f"Error processing data packet: {e}")
                    
            # Update windows based on BiF
            if validPkt and port in flows:
                try:
                    if SMOOTHENING and len(flows[port]["windows"]) > 2:
                        flows[port]["windows"].append(int((s_factor*flows[port]["windows"][-1]) + 
                                                       ((1-s_factor)*flows[port]["bif"])))
                    else:
                        flows[port]["windows"].append(int(flows[port]["bif"]))
                except (ValueError, TypeError) as e:
                    print(f"Error updating windows: {e}")
                    
            try:
                if packet.get("frame_len"):
                    total_bytes += int(packet.get("frame_len"))
            except ValueError:
                pass
                
            line_count += 1
            
        print(f"Processed {line_count} packets, {total_bytes/1000} KBytes for {cc}")
        
        # Remove flows with no windows data
        flows = {k: v for k, v in flows.items() if v["windows"]}
        
    return flows

def custom_smooth_function():
    pass

def get_flow_stats(flows):
    num=len(flows.keys())
    print("FLOW STATISTICS: \nNumber of flows: ", num)
    print("------------------------------------------------------------------------------")
    print('%6s'%"port", '%15s'%"SrcIP", '%8s'%"SrcPort",  '%8s'%"duration",  '%8s'%"start",  '%8s'%"end", '%8s'%"Sent (B)", '%8s'%"Recv (B)",)
    for k in flows.keys():
        print('%6s'%k, '%15s'%flows[k]["serverip"], '%8s'%flows[k]["serverport"], '%8s'%str('%.2f'%(flows[k]["times"][-1]-flows[k]["times"][0])), '%8s'%str('%.2f'%flows[k]["times"][0]), '%8s'%str('%.2f'%flows[k]["times"][-1]), '%8s'%flows[k]["last_seq"], '%8s'%flows[k]["last_ack"])
        #print("    * Flow "+str(k)+": ", flows[k]["last_ack"], " ", flows[k]["last_seq"], " bytes transfered.")
    return num

files=sys.argv[1:]
for f in files:
    algo_cc=f
    #Get the data for all the flows
    print("==============================================================================")
    print("opening trace ../candidates-measurements/"+algo_cc+".csv...")
    flows = process_flows(algo_cc, "../candidates-measurements/")
    #decide on final graph layout
    num = get_flow_stats(flows)

    if ONLY_STATS:
        sys.exit()
    
    if num==1:
        MULTI_GRAPH=False
    #grid size
    if MULTI_GRAPH:
        size=(0,0)
        grids={1:(2,2), 2:(2,2), 4:(2,2), 6:(2,3), 9:(3,3), 12:(3,4), 15:(3,5), 16:(4,4), 20:(5,4), 24:(6,4), 30:(6,5), 36:(6,6), 40:(8,5), 42:(8,7), 49:(7,7)}
        g=num
        while g<=49 and g not in grids:
            g+=1
        if g in grids.keys():
            size=grids[g]
        else:
            size=grids[49]  
        fig, axs = plt.subplots(size[0], size[1])
        for i in range(size[0]):
            for j in range(size[1]):
                #axs[i][j].legend(loc="lower right")
                if i==size[0]-1:
                    axs[i][j].set_xlabel("Time (s)")
                if j==0:
                    axs[i][j].set_ylabel("Bytes in flight")
    else:
        plt.figure(figsize=(30,15))
        plt.title(algo_cc)
        plt.xlabel("Time (s)")
        plt.ylabel("Bytes in flight")
    counter=0
    for port in flows.keys():
        if MULTI_GRAPH:  
            axs[counter%size[0]][(counter//size[0])%size[1]].scatter(flows[port]["times"], flows[port]["windows"], color="#858585")
            axs[counter%size[0]][(counter//size[0])%size[1]].plot(flows[port]["times"], flows[port]["windows"], label=str(port), linestyle="solid")
        else:

            plt.plot(flows[port]["times"], flows[port]["windows"], label=str(port), linestyle="solid", lw=0.5)
            plt.scatter(flows[port]["times"], flows[port]["windows"], color="r", s=5)
        counter+=1
    if MULTI_GRAPH:
        counter=0
        for port in flows.keys():
            axs[counter%size[0]][(counter//size[0])%size[1]].legend()
            counter+=1
    else:
        plt.legend()
    if MULTI_GRAPH:
        fig.set_size_inches(16, 12)
    if SHOW:
        plt.show()
    else:
        plt.savefig("../logs/plots/"+algo_cc+".png", dpi=600, bbox_inches='tight', pad_inches=0)

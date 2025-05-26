#!/usr/bin/env python3
"""
Debug script to check BiF extraction from a single trace file
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bif_lakshay import process_flows

def debug_single_trace(filename):
    """Debug a single trace file"""
    print(f"Debugging trace: {filename}")
    
    # Extract just the algorithm name
    basename = os.path.basename(filename)
    algo_name = basename.replace("-tcp.csv", "")
    dir_path = os.path.dirname(filename) + "/"
    
    print(f"Algorithm: {algo_name}")
    print(f"Directory: {dir_path}")
    
    # Process the flows with debug output
    flows = process_flows(algo_name, dir_path, p="y")
    
    print(f"\nFound {len(flows)} flows:")
    
    for port, flow_data in flows.items():
        print(f"\nFlow on port {port}:")
        print(f"  Server: {flow_data['serverip']}:{flow_data['serverport']}")
        print(f"  Duration: {flow_data['times'][-1] - flow_data['times'][0]:.2f}s")
        print(f"  Total packets: {len(flow_data['times'])}")
        print(f"  BiF values: min={min(flow_data['windows'])}, max={max(flow_data['windows'])}, avg={sum(flow_data['windows'])/len(flow_data['windows']):.1f}")
        print(f"  BiF variation: {max(flow_data['windows']) - min(flow_data['windows'])}")
        
        # Show first 10 BiF values
        print(f"  First 10 BiF values: {flow_data['windows'][:10]}")
        
        # Check if data is constant
        if len(set(flow_data['windows'])) == 1:
            print(f"  ❌ WARNING: All BiF values are identical ({flow_data['windows'][0]})")
        elif max(flow_data['windows']) - min(flow_data['windows']) < 1000:
            print(f"  ⚠️  WARNING: Very low BiF variation ({max(flow_data['windows']) - min(flow_data['windows'])} bytes)")
        else:
            print(f"  ✅ BiF shows variation")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 debug_bif.py <trace_file.csv>")
        print("Example: python3 debug_bif.py ../measurements/cubic-v1-5-50-200-2-tcp.csv")
        sys.exit(1)
    
    debug_single_trace(sys.argv[1])
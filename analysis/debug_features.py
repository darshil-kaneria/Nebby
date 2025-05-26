#!/usr/bin/env python3
"""
Debug script to check feature extraction from BiF traces
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from features_lakshay import get_plot_features, plot_one_bt

def debug_features(filename):
    """Debug feature extraction from a trace file"""
    print(f"Debugging feature extraction: {filename}")
    
    # Extract just the algorithm name  
    basename = os.path.basename(filename)
    algo_name = basename.replace("-tcp.csv", "")
    
    print(f"Algorithm: {algo_name}")
    
    try:
        # Get the smoothed BiF trace and retransmissions
        time, data, retrans, rtt = plot_one_bt(algo_name, p="n", t=1)
        
        print(f"\nAfter smoothing:")
        print(f"  Time points: {len(time)}")
        print(f"  Data points: {len(data)}")
        print(f"  RTT: {rtt:.3f}s")
        print(f"  Retransmissions: {len(retrans)}")
        print(f"  Data variation: {max(data) - min(data):.1f}")
        
        if len(data) == 0:
            print("❌ No data points after smoothing!")
            return
            
        if max(data) - min(data) < 1:
            print("❌ No variation in smoothed data!")
            return
            
        # Try to extract features
        time_full, data_full, features = get_plot_features(algo_name, p="n")
        
        print(f"\nFeature extraction:")
        print(f"  Number of features found: {len(features)}")
        
        if len(features) == 0:
            print("❌ No features extracted!")
            print(f"  This usually means no segments found between retransmissions")
            print(f"  Retransmission times: {retrans[:10]}...")  # Show first 10
        else:
            print("✅ Features extracted successfully")
            for i, feature in enumerate(features):
                start_idx, end_idx = feature
                duration = time_full[end_idx] - time_full[start_idx] 
                variation = max(data_full[start_idx:end_idx+1]) - min(data_full[start_idx:end_idx+1])
                print(f"  Feature {i+1}: duration={duration:.2f}s, variation={variation:.1f}")
        
    except Exception as e:
        print(f"❌ Error during feature extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 debug_features.py <trace_file.csv>")
        print("Example: python3 debug_features.py ../measurements/cubic-v1-5-50-200-2-tcp.csv")
        sys.exit(1)
    
    debug_features(sys.argv[1])
#!/usr/bin/env python3
"""Debug the entire feature processing pipeline step by step"""

import sys
import os
import numpy as np
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from features_lakshay import get_plot_features, plot_one_bt
from fit_lakshay import sample_data_time, normalize

def debug_full_pipeline(filename):
    """Debug each step of the feature processing pipeline"""
    
    print(f"=== DEBUGGING FEATURE PIPELINE ===")
    print(f"File: {filename}")
    
    basename = os.path.basename(filename)
    algo_name = basename.replace("-tcp.csv", "")
    
    try:
        # Step 1: Get features from BiF trace
        print(f"\n1. Feature extraction...")
        time, data, features = get_plot_features(algo_name, p="n")
        print(f"   Features found: {len(features)}")
        print(f"   Total data points: {len(data)}")
        print(f"   Data range: {max(data) - min(data):.1f}")
        
        if not features:
            print("   ❌ No features found!")
            return
        
        # Step 2: Process first feature through the pipeline
        feature = features[0]  # Take first feature
        start_idx, end_idx = feature
        curr_time = time[start_idx:end_idx+1]
        curr_data = data[start_idx:end_idx+1]
        
        print(f"\n2. First feature segment...")
        print(f"   Segment length: {len(curr_data)}")
        print(f"   Data range: {max(curr_data) - min(curr_data):.1f}")
        print(f"   Data variation (std): {np.std(curr_data):.1f}")
        
        # Step 3: sample_data_time
        print(f"\n3. Sample data time...")
        tr_time, tr_data = sample_data_time(curr_time, curr_data, 225, 1000)
        print(f"   After sampling: {len(tr_data)} points")
        if tr_data:
            print(f"   Data range: {max(tr_data) - min(tr_data):.1f}")
            print(f"   Data variation (std): {np.std(tr_data):.1f}")
        else:
            print("   ❌ No data after sampling!")
            return
        
        # Step 4: Rolling window smoothing
        print(f"\n4. Rolling window smoothing...")
        tr_time_pd = pd.DataFrame(tr_time)
        tr_data_pd = pd.DataFrame(tr_data)
        
        print(f"   Before rolling: {len(tr_data)} points, range: {max(tr_data) - min(tr_data):.1f}")
        
        tr_time_smooth = list(tr_time_pd.rolling(25, center=True).mean().dropna()[0])
        tr_data_smooth = list(tr_data_pd.rolling(25, center=True).mean().dropna()[0])
        
        print(f"   After rolling: {len(tr_data_smooth)} points")
        if tr_data_smooth:
            print(f"   Data range: {max(tr_data_smooth) - min(tr_data_smooth):.1f}")
            print(f"   Data variation (std): {np.std(tr_data_smooth):.1f}")
        else:
            print("   ❌ No data after rolling window!")
            return
        
        # Step 5: Normalization (RTT and BDP calculation)
        print(f"\n5. Normalization...")
        f_split = algo_name.split("-")
        rtt = float((int(f_split[2]) + int(f_split[3]))*2)/1000
        bdp = float(rtt*1000*int(f_split[4])*int(f_split[5]))/8
        
        print(f"   RTT: {rtt:.3f}, BDP: {bdp:.1f}")
        
        norm_time, norm_data = normalize(tr_time_smooth, tr_data_smooth, rtt, bdp)
        
        print(f"   After normalization: {len(norm_data)} points")
        if norm_data:
            print(f"   Data range: {max(norm_data) - min(norm_data):.6f}")
            print(f"   Data variation (std): {np.std(norm_data):.6f}")
            
            if max(norm_data) - min(norm_data) < 1e-6:
                print("   ❌ PROBLEM: Data becomes constant after normalization!")
            else:
                print("   ✅ Data still has variation after normalization")
        
        # Print first few values for inspection
        print(f"\n6. Sample values at each step:")
        print(f"   Original segment: {curr_data[:5]}...")
        print(f"   After sampling: {tr_data[:5]}...")
        print(f"   After smoothing: {tr_data_smooth[:5]}...")
        print(f"   After normalization: {norm_data[:5]}...")
        
    except Exception as e:
        print(f"❌ Error in pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 debug_pipeline.py <trace_file.csv>")
        print("Example: python3 debug_pipeline.py ../measurements/cubic-v1-5-50-200-2-tcp.csv")
        sys.exit(1)
    
    debug_full_pipeline(sys.argv[1])
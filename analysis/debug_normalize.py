#!/usr/bin/env python3
"""Debug the normalization step that's causing data to become constant"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_normalize_step():
    # Simulate the normalization from fit_lakshay.py
    
    # Example from your filename: cubic-v1-5-50-200-2
    f_split = "cubic-v1-5-50-200-2".split("-")
    print(f"File split: {f_split}")
    
    # RTT calculation from the code
    rtt = float((int(f_split[2]) + int(f_split[3]))*2)/1000
    print(f"RTT calculation: ({f_split[2]} + {f_split[3]}) * 2 / 1000 = {rtt}")
    
    # BDP calculation from the code  
    bdp = float(rtt*1000*int(f_split[4])*int(f_split[5]))/8
    print(f"BDP calculation: {rtt} * 1000 * {f_split[4]} * {f_split[5]} / 8 = {bdp}")
    
    # Simulate some realistic BiF data (from your debug output)
    import numpy as np
    sample_data = np.array([2000, 5000, 10000, 15000, 20000, 25000, 30000])
    sample_time = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    
    print(f"\nOriginal data:")
    print(f"  Time: {sample_time}")
    print(f"  Data: {sample_data}")
    print(f"  Data range: {np.max(sample_data) - np.min(sample_data)}")
    
    # Apply normalization from the code
    new_time = (sample_time/rtt)
    new_data = (sample_data/bdp)*100
    new_time -= min(new_time)
    new_data -= min(new_data)
    
    print(f"\nAfter normalization:")
    print(f"  Time: {new_time}")
    print(f"  Data: {new_data}")
    print(f"  Data range: {np.max(new_data) - np.min(new_data)}")
    print(f"  Data variation: {np.std(new_data)}")
    
    if np.max(new_data) - np.min(new_data) < 1e-10:
        print("❌ PROBLEM: Data becomes constant after normalization!")
        print("This is why polynomial fitting fails.")
        
        # Suggest fix
        print("\nSUGGESTED FIX:")
        print("The BDP calculation is too aggressive. Try:")
        print("1. Skip BDP normalization entirely")
        print("2. Use a smaller normalization factor")
        print("3. Use relative normalization instead")
        
        # Try alternative normalization
        alt_data = (sample_data / np.max(sample_data)) * 100
        alt_data -= min(alt_data)
        print(f"\nAlternative normalization (by max value):")
        print(f"  Data: {alt_data}")
        print(f"  Range: {np.max(alt_data) - np.min(alt_data)}")
    else:
        print("✅ Normalization preserves variation")

if __name__ == "__main__":
    debug_normalize_step()
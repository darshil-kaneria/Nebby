#!/usr/bin/env python3
"""
flow_visualizer.py - Plot BiF vs time for multiple flows

This script finds all flows identified in a Nebby analysis and
generates BiF vs time plots for each one, with special highlighting
for video and audio flows.

Usage: python flow_visualizer.py <run_id>
Example: python flow_visualizer.py cubic-20230501_120000
"""

import sys
import os
import json
import matplotlib.pyplot as plt
import numpy as np

# Import Nebby's existing functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from bif_lakshay import process_flows
    from features_lakshay import plot_one_bt, get_window
    print("Successfully imported Nebby modules")
except ImportError as e:
    print(f"Error importing Nebby modules: {e}")
    print("Make sure you're running this from the analysis directory")
    sys.exit(1)

def get_flow_types(measurement_dir, run_id):
    """Get flow type information from JSON file"""
    flow_types_file = os.path.join(measurement_dir, f"{run_id}-flow-types.json")
    if os.path.exists(flow_types_file):
        with open(flow_types_file, 'r') as f:
            return json.load(f)
    else:
        print(f"Flow types file not found: {flow_types_file}")
        return {}

def plot_flows(measurement_dir, run_id, show_plots=True):
    """Generate BiF vs time plots for all flows"""
    
    # Get flow type information
    flow_types = get_flow_types(measurement_dir, run_id)
    
    # Get all the flows from the TCP CSV
    flows = process_flows(run_id, measurement_dir, p="n")
    
    if not flows:
        print(f"No flows found for {run_id}")
        return
    
    print(f"Found {len(flows)} flows")
    
    # Create plots directory
    plots_dir = os.path.join(measurement_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # For each flow, generate a BiF plot
    for port in flows.keys():
        flow_type = flow_types.get(port, {}).get('type', 'unknown')
        content_type = flow_types.get(port, {}).get('content_type', 'unknown')
        
        # Create both 50ms and 100ms plots using Nebby's built-in function
        print(f"Plotting flow on port {port} ({flow_type})")
        
        try:
            # Generate a combined plot showing both network profiles
            plt.figure(figsize=(12, 6))
            
            # Plot raw BiF data
            time = flows[port]['times']
            bif = flows[port]['windows']
            
            plt.plot(time, bif, 'b-', label='Raw BiF')
            
            # Mark retransmissions if available
            if 'retrans' in flows[port]:
                for t in flows[port]['retrans']:
                    plt.axvline(x=t, color='r', alpha=0.3)
            
            # Create title and labels
            plt.title(f"BiF vs Time for {run_id} (Port {port} - {flow_type})")
            plt.xlabel("Time (s)")
            plt.ylabel("Bytes in Flight")
            
            # Add content type information
            plt.figtext(0.5, 0.01, f"Content Type: {content_type}", 
                       ha="center", fontsize=10, 
                       bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
            
            # Add legend
            plt.legend()
            
            # Save the plot
            plot_file = os.path.join(plots_dir, f"{run_id}-port-{port}-{flow_type}.png")
            plt.savefig(plot_file)
            print(f"Plot saved to {plot_file}")
            
            # Show the plot if requested
            if show_plots:
                plt.show()
            else:
                plt.close()
                
        except Exception as e:
            print(f"Error plotting flow on port {port}: {e}")
    
    # Create a summary plot showing all flows together
    try:
        plt.figure(figsize=(15, 8))
        
        # Plot each flow with a different color
        for port in flows.keys():
            flow_type = flow_types.get(port, {}).get('type', 'unknown')
            time = flows[port]['times']
            bif = flows[port]['windows']
            
            # Use different colors for different content types
            if flow_type == 'video':
                color = 'r'  # Red for video
                alpha = 1.0
                zorder = 10  # Bring to front
            elif flow_type == 'audio':
                color = 'g'  # Green for audio
                alpha = 0.9
                zorder = 9
            elif flow_type == 'data':
                color = 'b'  # Blue for data
                alpha = 0.7
                zorder = 8
            else:
                color = 'gray'  # Gray for everything else
                alpha = 0.5
                zorder = 5
            
            plt.plot(time, bif, color=color, alpha=alpha, 
                    label=f"Port {port} ({flow_type})", zorder=zorder)
        
        # Create title and labels
        plt.title(f"All Flows for {run_id}")
        plt.xlabel("Time (s)")
        plt.ylabel("Bytes in Flight")
        
        # Add legend
        plt.legend()
        
        # Save the plot
        summary_plot = os.path.join(plots_dir, f"{run_id}-all-flows.png")
        plt.savefig(summary_plot)
        print(f"Summary plot saved to {summary_plot}")
        
        # Show the plot if requested
        if show_plots:
            plt.show()
        else:
            plt.close()
            
    except Exception as e:
        print(f"Error creating summary plot: {e}")
    
    return plots_dir

def main():
    if len(sys.argv) < 2:
        print("Usage: python flow_visualizer.py <run_id> [measurement_dir]")
        print("Example: python flow_visualizer.py cubic-20230501_120000")
        sys.exit(1)
    
    run_id = sys.argv[1]
    measurement_dir = sys.argv[2] if len(sys.argv) > 2 else f"../measurements/{run_id}/"
    
    # Check if directory exists
    if not os.path.exists(measurement_dir):
        print(f"Measurement directory not found: {measurement_dir}")
        sys.exit(1)
    
    # Generate plots
    plots_dir = plot_flows(measurement_dir, run_id)
    
    print(f"All plots saved to {plots_dir}")

if __name__ == "__main__":
    main()
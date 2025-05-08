#!/usr/bin/env python3
"""
Fixed process_video_flows.py
Handles the specific CSV format produced by tshark and properly processes Chrome's network log
"""

import sys
import json
import csv
import os

def identify_flow_types(netlog_file, tcp_csv_file):
    """Identify video and non-video flows from Chrome network log"""
    
    # First, ensure the files exist
    if not os.path.exists(netlog_file):
        print(f"ERROR: Network log file not found: {netlog_file}")
        return {}
        
    if not os.path.exists(tcp_csv_file):
        print(f"ERROR: TCP CSV file not found: {tcp_csv_file}")
        return {}
    
    # Debug: print first few lines of the TCP CSV to see its format
    print(f"Examining TCP CSV file: {tcp_csv_file}")
    with open(tcp_csv_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 3:  # Print first 3 lines
                print(f"Line {i}: {line.strip()}")
    
    # Read the TCP CSV to get port information
    ports = set()
    try:
        with open(tcp_csv_file, 'r') as f:
            reader = csv.reader(f)
            # Try to read header
            headers = next(reader, [])
            
            print(f"CSV Headers: {headers}")
            
            # Find port column indexes - handle different formats
            src_port_idx = -1
            dest_port_idx = -1
            
            for i, header in enumerate(headers):
                if header == 'tcp.srcport':
                    src_port_idx = i
                if header == 'tcp.dstport':
                    dest_port_idx = i
            
            print(f"Using port indexes: src_port_idx={src_port_idx}, dest_port_idx={dest_port_idx}")
            
            # Collect all ports
            port_count = 0
            for row in reader:
                try:
                    if len(row) > max(src_port_idx, dest_port_idx) and src_port_idx >= 0 and dest_port_idx >= 0:
                        # Get source port
                        if row[src_port_idx] and row[src_port_idx] != '""':
                            src_port = row[src_port_idx].strip('"')
                            if src_port:
                                ports.add(src_port)
                                port_count += 1
                        
                        # Get destination port
                        if row[dest_port_idx] and row[dest_port_idx] != '""':
                            dst_port = row[dest_port_idx].strip('"')
                            if dst_port:
                                ports.add(dst_port)
                                port_count += 1
                except Exception as e:
                    print(f"Error processing row {reader.line_num}: {e}")
                    print(f"Row data: {row}")
                    continue
            
            print(f"Found {len(ports)} unique ports from {port_count} port entries")
            
            # If no ports found, try manual extraction
            if not ports:
                print("Trying manual port extraction...")
                f.seek(0)
                next(f)  # Skip header
                for line in f:
                    parts = line.split(',')
                    if len(parts) > 4:
                        if parts[2] and parts[2] != '""':
                            ports.add(parts[2].strip('"'))
                        if parts[4] and parts[4] != '""':
                            ports.add(parts[4].strip('"'))
                
                print(f"Manual extraction found {len(ports)} ports")
    except Exception as e:
        print(f"Error reading TCP CSV: {e}")
        return {}
    
    print(f"Found ports: {ports}")
    
    # Now parse the Chrome network log
    flow_types = {}
    try:
        with open(netlog_file, 'r') as f:
            try:
                data = json.load(f)
                
                # Process network events
                if 'events' in data:
                    event_count = len(data['events'])
                    print(f"Processing {event_count} events from network log")
                    
                    # First collect all socket connections with port info
                    socket_ports = {}
                    
                    for event in data['events']:
                        # Look for SOCKET_CONNECT events to get port information
                        if event.get('type') == 'SOCKET_CONNECT' and 'params' in event:
                            params = event.get('params', {})
                            if 'address' in params:
                                address = params['address']
                                if ':' in address:
                                    # Extract port from socket address (format: "ip:port")
                                    port = address.split(':')[-1]
                                    socket_id = event.get('source', {}).get('id')
                                    if socket_id and port:
                                        socket_ports[socket_id] = port
                    
                    print(f"Found {len(socket_ports)} socket connections with port information")
                    
                    # Now look for HTTP transactions
                    for event in data['events']:
                        # Look for HTTP response headers
                        if event.get('type') == 'HTTP_TRANSACTION_READ_RESPONSE_HEADERS' and 'params' in event:
                            params = event.get('params', {})
                            headers = params.get('headers', [])
                            
                            # Extract content type
                            content_type = 'unknown'
                            for header in headers:
                                if isinstance(header, str) and header.lower().startswith('content-type:'):
                                    content_type = header.split(':', 1)[1].strip()
                                    break
                            
                            # Get the socket ID for this transaction
                            socket_id = params.get('socket_id')
                            
                            # Find the port for this socket
                            port = socket_ports.get(socket_id)
                            
                            if port and port in ports:
                                if 'video' in content_type.lower():
                                    flow_type = 'video'
                                elif 'audio' in content_type.lower():
                                    flow_type = 'audio'
                                elif 'json' in content_type.lower():
                                    flow_type = 'data'
                                elif 'javascript' in content_type.lower():
                                    flow_type = 'script'
                                else:
                                    flow_type = 'other'
                                    
                                flow_types[port] = {
                                    'type': flow_type,
                                    'content_type': content_type,
                                    'url': params.get('url', '')
                                }
                else:
                    print("WARNING: No 'events' found in network log")
            except json.JSONDecodeError as e:
                print(f"Error parsing network log JSON: {e}")
                # Try to fix the JSON file
                f.seek(0)
                content = f.read()
                # Attempt to fix common JSON issues
                if content.endswith(','):
                    content = content.rstrip(',') + ']}' 
                    fixed_json = json.loads(content)
                    print("Successfully fixed JSON")
                    # Continue processing with fixed JSON
                    # ...
    except Exception as e:
        print(f"Error processing network log: {e}")
        return {}
    
    # Fallback: if we couldn't identify any flows but we have ports, create placeholder entries
    if not flow_types and ports:
        print("Could not identify flow types from network log, using placeholders")
        for port in ports:
            flow_types[port] = {
                'type': 'unknown',
                'content_type': 'unknown'
            }
    
    return flow_types

def main():
    if len(sys.argv) != 3:
        print("Usage: python process_video_flows.py <netlog_file> <tcp_csv_file>")
        return
    
    netlog_file = sys.argv[1]
    tcp_csv_file = sys.argv[2]
    
    print(f"Processing:\n  Network log: {netlog_file}\n  TCP CSV: {tcp_csv_file}")
    
    # Identify flow types
    flow_types = identify_flow_types(netlog_file, tcp_csv_file)
    
    # Output directory (same as measurement files)
    output_dir = os.path.dirname(tcp_csv_file)
    base_name = os.path.basename(tcp_csv_file)
    
    # Generate output filename
    if base_name.endswith('-tcp.csv'):
        output_name = base_name[:-8] + '-flow-types.json'
    else:
        output_name = base_name + '-flow-types.json'
    
    # Print results
    print("\nFlow Types:")
    print(f"{'Port':<10} {'Type':<15} {'Content Type':<30}")
    print("-" * 60)
    
    video_count = 0
    audio_count = 0
    other_count = 0
    
    for port, info in flow_types.items():
        print(f"{port:<10} {info['type']:<15} {info['content_type']:<30}")
        if info['type'] == 'video':
            video_count += 1
        elif info['type'] == 'audio':
            audio_count += 1
        else:
            other_count += 1
    
    print(f"\nSummary: {video_count} video flows, {audio_count} audio flows, {other_count} other flows")
    
    # Save results
    output_file = os.path.join(output_dir, output_name)
    with open(output_file, 'w') as f:
        json.dump(flow_types, f, indent=2)
    
    print(f"\nFlow type information saved to {output_file}")

if __name__ == "__main__":
    main()
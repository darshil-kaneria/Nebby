#!/bin/bash
# rename-files.sh - Updated for multiple traces per CCA

MEASUREMENTS_DIR="./measurements"

echo "Renaming trace files to analysis format..."

for file in "$MEASUREMENTS_DIR"/*-tcp.csv; do
  basename=$(basename "$file" -tcp.csv)
  
  # Check if file already has the correct format (5 dashes: algo-v#-pre-post-speed-buff)
  if [[ "$basename" == *-*-*-*-*-* ]]; then
    echo "File $basename already has the correct format"
    continue
  fi
  
  # Parse the new naming scheme: algo-v#-tcp.csv or algo-100ms-v#-tcp.csv
  if [[ "$basename" =~ ^(.+)-100ms-v([0-9]+)$ ]]; then
    # Format: algo-100ms-v# (e.g., cubic-100ms-v1)
    algo="${BASH_REMATCH[1]}"
    trace_num="${BASH_REMATCH[2]}"
    pre_delay=5
    post_delay=100
  elif [[ "$basename" =~ ^(.+)-v([0-9]+)$ ]]; then
    # Format: algo-v# (e.g., cubic-v1)
    algo="${BASH_REMATCH[1]}"
    trace_num="${BASH_REMATCH[2]}"
    pre_delay=5
    post_delay=50
  else
    # Legacy format: algo or algo-100ms
    if [[ "$basename" == *-100ms ]]; then
      algo=${basename%-100ms}
      trace_num=1
      pre_delay=5
      post_delay=100
    else
      algo=$basename
      trace_num=1
      pre_delay=5
      post_delay=50
    fi
  fi
  
  link_speed=200
  buff_size=2
  
  # Create new filename: algo-v#-pre-post-speed-buff
  new_basename="${algo}-v${trace_num}-${pre_delay}-${post_delay}-${link_speed}-${buff_size}"
  
  echo "Renaming $basename to $new_basename"
  mv "$file" "$MEASUREMENTS_DIR/${new_basename}-tcp.csv"
  
  # Also rename corresponding UDP file if it exists
  if [ -f "$MEASUREMENTS_DIR/${basename}-udp.csv" ]; then
    mv "$MEASUREMENTS_DIR/${basename}-udp.csv" "$MEASUREMENTS_DIR/${new_basename}-udp.csv"
  fi
done

echo "Renaming complete!"

# Show summary of renamed files
echo ""
echo "Summary of traces per CCA:"
for cca in $(ls "$MEASUREMENTS_DIR"/*-tcp.csv | sed 's/.*\///g' | sed 's/-v[0-9]*-.*//g' | sort | uniq); do
  count=$(ls "$MEASUREMENTS_DIR"/${cca}-v*-tcp.csv 2>/dev/null | wc -l)
  if [ $count -gt 0 ]; then
    echo "  $cca: $count traces"
  fi
done
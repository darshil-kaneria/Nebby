#!/bin/bash
# fix-filenames.sh

MEASUREMENTS_DIR="./candidates-measurements"

# Rename files to match the expected format
for file in "$MEASUREMENTS_DIR"/*-tcp.csv; do
  basename=$(basename "$file" -tcp.csv)
  
  # Skip files that already have the right format
  if [[ "$basename" == *-*-*-*-* ]]; then
    echo "File $basename already has the correct format"
    continue
  fi
  
  # Extract the delay from filename (if present)
  if [[ "$basename" == *-100ms ]]; then
    # This is a 100ms delay test
    algo=${basename%-100ms}
    pre_delay=5
    post_delay=100
  else
    # This is a 50ms delay test
    algo=$basename
    pre_delay=5
    post_delay=50
  fi
  
  # Use standard values for other parameters
  link_speed=200
  buff_size=2
  
  # Create new filename
  new_basename="${algo}-v1-${pre_delay}-${post_delay}-${link_speed}-${buff_size}"
  
  echo "Renaming $basename to $new_basename"
  mv "$file" "$MEASUREMENTS_DIR/${new_basename}-tcp.csv"
  
  # Also rename UDP file if it exists
  if [ -f "$MEASUREMENTS_DIR/${basename}-udp.csv" ]; then
    mv "$MEASUREMENTS_DIR/${basename}-udp.csv" "$MEASUREMENTS_DIR/${new_basename}-udp.csv"
  fi
done

echo "Files renamed successfully"
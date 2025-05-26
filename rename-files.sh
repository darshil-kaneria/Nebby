#!/bin/bash
# fix-filenames.sh

MEASUREMENTS_DIR="./scripts/reference_traces"

for file in "$MEASUREMENTS_DIR"/*-tcp.csv; do
  basename=$(basename "$file" -tcp.csv)
  
  if [[ "$basename" == *-*-*-*-* ]]; then
    echo "File $basename already has the correct format"
    continue
  fi
  
  if [[ "$basename" == *-100ms ]]; then
    algo=${basename%-100ms}
    pre_delay=5
    post_delay=100
  else
    algo=$basename
    pre_delay=5
    post_delay=50
  fi
  
  link_speed=200
  buff_size=2
  
  new_basename="${algo}-v1-${pre_delay}-${post_delay}-${link_speed}-${buff_size}"
  
  echo "Renaming $basename to $new_basename"
  mv "$file" "$MEASUREMENTS_DIR/${new_basename}-tcp.csv"
  
  if [ -f "$MEASUREMENTS_DIR/${basename}-udp.csv" ]; then
    mv "$MEASUREMENTS_DIR/${basename}-udp.csv" "$MEASUREMENTS_DIR/${new_basename}-udp.csv"
  fi
done
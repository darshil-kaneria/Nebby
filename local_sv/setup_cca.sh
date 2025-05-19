#!/bin/bash

# Added test data creation to script
mkdir -p nebby-data
dd if=/dev/urandom of=nebby-data/test-400kb.bin bs=1024 count=400
dd if=/dev/urandom of=nebby-data/test-1mb.bin bs=1024 count=1024
echo "<html><body><h1>Test Page for Nebby</h1></body></html>" > nebby-data/index.html

AVAILABLE_CCAS=$(cat /proc/sys/net/ipv4/tcp_available_congestion_control)
echo "Available CCAs on host: $AVAILABLE_CCAS"

read -r -a CCAS <<< "$AVAILABLE_CCAS"

# Need to clean up existing containers...
docker stop $(docker ps -a -q --filter "name=nebby-" 2>/dev/null) 2>/dev/null
docker rm $(docker ps -a -q --filter "name=nebby-" 2>/dev/null) 2>/dev/null

cat > Dockerfile.cca << 'EOF'
FROM node:slim
WORKDIR /app
RUN apt-get update && apt-get install -y procps
RUN npm install -g http-server
WORKDIR /data

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Setting CCA to $CCA"\n\
sysctl -w net.ipv4.tcp_congestion_control=$CCA\n\
http-server -p $PORT' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
EOF

docker build -f Dockerfile.cca -t nebby-cca-base .

BASE_PORT=8000
for cca in "${CCAS[@]}"; do
  echo "Setting up $cca on port $BASE_PORT..."
  
  docker run -d --name "nebby-$cca" \
    --network=host \
    --privileged \
    -e CCA=$cca \
    -e PORT=$BASE_PORT \
    -v "$(pwd)/nebby-data:/data" \
    nebby-cca-base
  
  sleep 1
  CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' nebby-$cca 2>/dev/null)
  if [ -n "$CONTAINER_PID" ]; then
    ACTUAL_CCA=$(docker exec nebby-$cca sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)
    if [ "$ACTUAL_CCA" == "$cca" ]; then
      echo "Successfully set $cca on port $BASE_PORT"
    else
      echo "Failed to set $cca (got: $ACTUAL_CCA or not available)"
      docker stop nebby-$cca
      docker rm nebby-$cca
    fi
  else
    echo "Container failed to start"
  fi
  
  BASE_PORT=$((BASE_PORT + 1))
done

echo "Servers running at:"
for container in $(docker ps --format '{{.Names}}' | grep "^nebby-"); do
  cca=${container#nebby-}
  PORT=$(docker exec $container env | grep PORT | cut -d= -f2)
  echo "http://localhost:$PORT/test-400kb.bin - $cca"
done
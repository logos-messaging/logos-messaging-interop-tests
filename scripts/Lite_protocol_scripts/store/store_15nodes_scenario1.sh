#!/bin/bash

set -e

# This implements a  waku-simulator with 15 nodes network, 1 service, 1 edge node added
# service node is limited to 1 cpu core with only 512 MB
# Runs different test phases with different load from sonda (STORE) side
# 1. 2 sonda instances, query every 500ms
# 2. 5 sonda instances, query every 200ms
# 3. 10 sonda instances, query every 100ms

echo "Running test..."

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Bringing up simulator at $current_time"

cd ./waku-simulator

# simulator exports
export NUM_NWAKU_NODES=15
export TRAFFIC_DELAY_SECONDS=15
export MSG_SIZE_KBYTES=10
export SERVICENODE_CPU_CORES="0-3"
export POSTGRES_CPU_CORES="0-3"

docker compose up -d
cd ..

echo "Waiting 30s for service node to be ready..."
sleep 30

cd ./sonda

# build sonda image
docker build -t local-perf-sonda -f Dockerfile.sonda .

#  2 sondas 500ms

cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.5
STORE_NODES=/ip4/127.0.0.1/tcp/60001/p2p/<SERVICE_PEER_ID>
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.95
EOF

docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 1 running 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

#5 sondas 200ms

cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.2
STORE_NODES=/ip4/127.0.0.1/tcp/60001/p2p/<SERVICE_PEER_ID>
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.95
EOF

docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 2 running 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

#10 sondas 100ms 
cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.1
STORE_NODES=/ip4/127.0.0.1/tcp/60001/p2p/<SERVICE_PEER_ID>
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.95
EOF

docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 3 running 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

cd ..

cd ./waku-simulator
docker compose down
cd ..

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Test finished at $current_time"

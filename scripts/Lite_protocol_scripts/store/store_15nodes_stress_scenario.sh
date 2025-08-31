#!/bin/bash


# waku-simulator with 15 nodes network, 1 service, 1 edge node added
# service node is limited to 1 cpu core with only 512 MB
# This scenario intended to stress test service node STORE queries with high request frequency
# Increasing number of sonda instances and decreasing query delay ms
# 16 sondas 100ms
# 16 sondas 50ms
# 24 sondas 50ms
# 24 sondas 20ms

set -e

echo "Running test..."

cd ./waku-simulator

export NUM_NWAKU_NODES=15
export TRAFFIC_DELAY_SECONDS=10
export MSG_SIZE_KBYTES=12

docker compose up -d
cd ..

echo "Waiting 30s for service node..."
sleep 30

cd ./sonda

docker build -t local-perf-sonda -f Dockerfile.sonda .

#16 sondas  100ms 
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
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 1 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

# 16 sondas 50ms
cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.05
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
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 2 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

# 24 sondas 50ms
cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.05
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
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 3 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

#24 sondas 20ms
cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.02
STORE_NODES=/ip4/127.0.0.1/tcp/60001/p2p/<SERVICE_PEER_ID>
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.95
EOF

docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
# repeat 23 more times
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
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

echo "Phase 4 300s..."
sleep 300
docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

cd ..

cd ./waku-simulator
docker compose down
cd ..

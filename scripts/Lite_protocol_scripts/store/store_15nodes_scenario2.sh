#!/bin/bash

set -e

echo "Running test..."

# This implements a short version of 1st store scenario.
# waku-simulator with 15 nodes network, 1 service, 1 edge node added
# service node is limited to 1 cpu core with only 512 MB
# Runs 1 phase with sonda load:
# 1. 10 sonda instances, each queries in every 100ms

cd ./waku-simulator

export NUM_NWAKU_NODES=15
export TRAFFIC_DELAY_SECONDS=10
export MSG_SIZE_KBYTES=8

docker compose up -d
cd ..

echo "Waiting 20s for service node..."
sleep 20

cd ./sonda

docker build -t local-perf-sonda -f Dockerfile.sonda .

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

echo "Phase running 300s..."
sleep 300

docker kill $(docker ps -q -f "label=sonda") >/dev/null 2>&1 || true

cd ..

cd ./waku-simulator
docker compose down
cd ..

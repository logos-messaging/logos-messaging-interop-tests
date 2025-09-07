#!/bin/bash
set -e

STORE_NODES="/ip4/10.2.0.101/tcp/60001/p2p/16Uiu2HAkyte8uj451tGkbww4Mjcg6DRnmAHxNeWyF4zp23RbpG3n,/ip4/10.2.0.102/tcp/60001/p2p/16Uiu2HA7abcDEF451tGkbzz4Mjcg6DRnmAHxNeWyF4zp23RbpXYZ2"
RELAY_NODE_REST_ADDRESS="http://127.0.0.1:8645"
STORE_NODE_REST_ADDRESS="http://127.0.0.1:8644"
PUBSUB_TOPIC="/waku/2/default-waku/proto"
CONTENT_TOPIC="/sonda/2/polls/proto"
PHASE_SLEEP=300

echo "Running test..."
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Bringing up simulator at $current_time"

cd ./waku-simulator
export SERVICENODE_CPU_CORES=0
export POSTGRES_CPU_CORES=1-3
export GF_SECURITY_ADMIN_USER=admin
export GF_SECURITY_ADMIN_PASSWORD=admin
docker compose up -d
while [ "$(docker inspect --format "{{.State.Status}}" $(docker compose ps -q servicenode))" != "running" ]; do
    sleep 1
done
cd ..

cd ./sonda
docker build -t local-perf-sonda -f ./Dockerfile.sonda .
cat > ./perf-test.env <<EOF
RELAY_NODE_REST_ADDRESS=${RELAY_NODE_REST_ADDRESS}
STORE_NODE_REST_ADDRESS=${STORE_NODE_REST_ADDRESS}
STORE_NODES=${STORE_NODES}
QUERY_DELAY=0.25
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.9
PUBSUB_TOPIC=${PUBSUB_TOPIC}
CONTENT_TOPIC=${CONTENT_TOPIC}
EOF
docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda
cd ..

cd ./lpt
export LPT_IMAGE=harbor.status.im/wakuorg/liteprotocoltester:latest
export START_PUBLISHING_AFTER=15
export MESSAGE_MIN_BYTES=2048
export MESSAGE_MAX_BYTES=32768
export NUM_PUBLISHER_NODES=10
export NUM_RECEIVER_NODES=10
export LIGHTPUSH_INTERVAL_MS=100
docker compose up -d
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- Phase 1: 10 pub / 10 recv (100ms, 2–32KB). Start: $current_time"
sleep ${PHASE_SLEEP}

docker compose down
export NUM_PUBLISHER_NODES=20
export NUM_RECEIVER_NODES=5
export MESSAGE_MIN_BYTES=4096
export MESSAGE_MAX_BYTES=65536
export LIGHTPUSH_INTERVAL_MS=80
docker compose up -d
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- Phase 2: 20 pub / 5 recv (80ms, 4–64KB). Start: $current_time"
sleep ${PHASE_SLEEP}

docker compose down
export NUM_PUBLISHER_NODES=5
export NUM_RECEIVER_NODES=20
export MESSAGE_MIN_BYTES=1024
export MESSAGE_MAX_BYTES=16384
export LIGHTPUSH_INTERVAL_MS=120
docker compose up -d
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- Phase 3: 5 pub / 20 recv (120ms, 1–16KB). Start: $current_time"
sleep ${PHASE_SLEEP}

docker compose down
export NUM_PUBLISHER_NODES=25
export NUM_RECEIVER_NODES=25
export MESSAGE_MIN_BYTES=2048
export MESSAGE_MAX_BYTES=32768
export LIGHTPUSH_INTERVAL_MS=90
docker compose up -d
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- Phase 4: 25 pub / 25 recv (90ms, 2–32KB). Start: $current_time"
sleep ${PHASE_SLEEP}

docker compose down receivernode
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- Phase 5: receivers down, publishers + Sonda only. Start: $current_time"
sleep ${PHASE_SLEEP}

docker compose down
cd ..
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Scenario finished at $current_time"

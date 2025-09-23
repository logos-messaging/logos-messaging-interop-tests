#!/bin/bash

set -e

# ------------------------------------------------------------------------------
# This implements a simple Store scenario, matching scenario_1.sh style:
# - Bring up waku-simulator
# - Wait for servicenode to be running (tight while loop like scenario_1.sh)
# - Start Sonda (publishes via relay & queries store) using perf-test.env
# - Start LPT (publishers/receivers) in phases: 2x2 -> 1x5 -> 5x1 -> receivers down -> lpt down
# ------------------------------------------------------------------------------

# >>> EDIT THESE IF YOUR SETUP DIFFERS <<<
STORE_NODES="/ip4/10.2.0.101/tcp/60001/p2p/16Uiu2HAkyte8uj451tGkbww4Mjcg6DRnmAHxNeWyF4zp23RbpG3n"
RELAY_NODE_REST_ADDRESS="http://127.0.0.1:8645"
STORE_NODE_REST_ADDRESS="http://127.0.0.1:8644"
PUBSUB_TOPIC="/waku/2/default-waku/proto"
CONTENT_TOPIC="/sonda/2/polls/proto"
# <<< EDIT ABOVE >>>

echo "Running test..."

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Bringing up simulator at $current_time"

cd ./waku-simulator

# same style: exports before compose
export SERVICENODE_CPU_CORES=0      # 1 core for service node
export POSTGRES_CPU_CORES=1-3       # keep DB off core 0
export GF_SECURITY_ADMIN_USER=admin
export GF_SECURITY_ADMIN_PASSWORD=admin
export NWAKU_IMAGE=wakuorg/nwaku:latest
export NUM_NWAKU_NODES=15
export RLN_ENABLED=false

docker compose up -d

# Wait for servicenode to be running (scenario_1.sh style)
while [ "$(docker inspect --format "{{.State.Status}}" $(docker compose ps -q servicenode))" != "running" ]; do
    sleep 1
done

cd ..

# ------------------------------------------------------------------------------
# Start Sonda (like scenario_1.sh: build & run with env-file, host network)
# ------------------------------------------------------------------------------
cd ./sonda

docker build -t local-perf-sonda -f ./Dockerfile.sonda .

cat > ./perf-test.env <<EOF
RELAY_NODE_REST_ADDRESS=${RELAY_NODE_REST_ADDRESS}
STORE_NODE_REST_ADDRESS=${STORE_NODE_REST_ADDRESS}
STORE_NODES=${STORE_NODES}
QUERY_DELAY=0.5
CLUSTER_ID=66
SHARD=0
HEALTH_THRESHOLD=0.9
PUBSUB_TOPIC=${PUBSUB_TOPIC}
CONTENT_TOPIC=${CONTENT_TOPIC}
EOF

docker run --env-file ./perf-test.env -l sonda -d --network host local-perf-sonda

cd ..

# ------------------------------------------------------------------------------
# Start LPT publishers/receivers in phases (exact same flow pattern as scenario_1.sh)
# ------------------------------------------------------------------------------
cd ./lpt

export LPT_IMAGE=harbor.status.im/wakuorg/liteprotocoltester:latest

## Define number of publisher and receiver nodes to run.
export NUM_PUBLISHER_NODES=2
export NUM_RECEIVER_NODES=2

## Can add some seconds delay before SENDER starts publishing
## Useful to let RECEIVER nodes to setup and subscribe ahead of expected messages being sent.
export START_PUBLISHING_AFTER=15

docker compose up -d

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- is running with 2 publisher and 2 receiver + sonda  from now: $current_time"

sleep 300

docker compose down
export NUM_PUBLISHER_NODES=1
export NUM_RECEIVER_NODES=5
docker compose up -d

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- is running with 1 publisher and 5 receiver from now: $current_time"

sleep 300

docker compose down
export NUM_PUBLISHER_NODES=5
export NUM_RECEIVER_NODES=1
docker compose up -d

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- is running with 5 publisher and 1 receiver from now: $current_time"

sleep 300

# switch off receiver (like scenario_1 “switch off filter” step)
docker compose down receivernode

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT- receiver nodes are down, sonda and lightpush publisher is working from now: $current_time"

sleep 300

# swtich off lightpush (leave only sonda)
docker compose down

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "LPT down, only sonda is working from now: $current_time"

sleep 300

cd ..

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Test finished at $current_time"

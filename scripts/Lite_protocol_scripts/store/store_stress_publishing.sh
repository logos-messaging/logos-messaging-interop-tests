#!/bin/bash
# Scenario 5  heavy publishing, then deep Store backfill queries with full JSON output.
set -e

STORE_NODES="/ip4/10.2.0.101/tcp/60001/p2p/16Uiu2HAkyte8uj451tGkbww4Mjcg6DRnmAHxNeWyF4zp23RbpG3n"
RELAY_NODE_REST_ADDRESS="http://127.0.0.1:8645"
STORE_NODE_REST_ADDRESS="http://127.0.0.1:8644"
PUBSUB_TOPIC="/waku/2/default-waku/proto"
CONTENT_TOPIC="/sonda/2/polls/proto"
PHASE_SLEEP=600

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
QUERY_DELAY=3
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
export NUM_PUBLISHER_NODES=30
export NUM_RECEIVER_NODES=10
export MESSAGE_MIN_BYTES=4096
export MESSAGE_MAX_BYTES=65536
export LIGHTPUSH_INTERVAL_MS=40
docker compose up -d
current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Warm-up: 30 pub / 10 recv (40ms, 4–64KB) $current_time"
sleep ${PHASE_SLEEP}
docker compose down
cd ..

NOW_TS=$(date +%s)
START_TS_2H=$(( NOW_TS - 7200 ))
START_TS_1H=$(( NOW_TS - 3600 ))
START_TS_30M=$(( NOW_TS - 1800 ))

echo "Backfill 2h window"
curl -G "${STORE_NODE_REST_ADDRESS}/store/v3/messages" \
  --data-urlencode "peerAddr=${STORE_NODES}" \
  --data-urlencode "pubsubTopic=${PUBSUB_TOPIC}" \
  --data-urlencode "contentTopics=[\"${CONTENT_TOPIC}\"]" \
  --data-urlencode "includeData=true" \
  --data-urlencode "startTime=${START_TS_2H}"

echo "Backfill 1h window"
curl -G "${STORE_NODE_REST_ADDRESS}/store/v3/messages" \
  --data-urlencode "peerAddr=${STORE_NODES}" \
  --data-urlencode "pubsubTopic=${PUBSUB_TOPIC}" \
  --data-urlencode "contentTopics=[\"${CONTENT_TOPIC}\"]" \
  --data-urlencode "includeData=true" \
  --data-urlencode "startTime=${START_TS_1H}"

echo "Backfill 30m window"
curl -G "${STORE_NODE_REST_ADDRESS}/store/v3/messages" \
  --data-urlencode "peerAddr=${STORE_NODES}" \
  --data-urlencode "pubsubTopic=${PUBSUB_TOPIC}" \
  --data-urlencode "contentTopics=[\"${CONTENT_TOPIC}\"]" \
  --data-urlencode "includeData=true" \
  --data-urlencode "startTime=${START_TS_30M}"

current_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Scenario 5 finished at $current_time"

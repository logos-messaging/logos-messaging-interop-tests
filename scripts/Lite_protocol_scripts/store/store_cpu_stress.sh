#!/bin/bash
set -e

# =========================
# IDs (same style)
# =========================
export SCENARIO_ID="cpu_store_stress"
export TEST_NAME="${SCENARIO_ID}_$(date +%Y%m%d_%H%M%S)"
echo "[${TEST_NAME}] start"

# =========================
# Images (match your scripts)
# =========================
export LPT_IMAGE="harbor.status.im/wakuorg/liteprotocoltester:latest"

# =========================
# Compose-required vars
# =========================
export GF_SECURITY_ADMIN_USER="admin"
export GF_SECURITY_ADMIN_PASSWORD="admin"
export NODEKEY="${NODEKEY:-}"
export STORAGE_SIZE="${STORAGE_SIZE:-}"

# =========================
# Resource knobs
# =========================
export SERVICENODE_CPU_CORES="0-1"
export POSTGRES_CPU_CORES="2-3"
export SERVICE_MEM_LIMIT="2g"
export POSTGRES_MEM_LIMIT="2g"
export POSTGRES_SHM_SIZE="1g"

# =========================
# Topic / shard
# =========================
export CLUSTER_ID=66
export SHARD=0
export PUBSUB_TOPIC="/waku/2/rs/${CLUSTER_ID}/${SHARD}"
export CONTENT_TOPIC="/sonda/2/polls/proto"

# =========================
# REST endpoints
# =========================
export RELAY_NODE_REST_ADDRESS="http://127.0.0.1:8645"
export STORE_NODE_REST_ADDRESS="http://127.0.0.1:8644"

# =========================
# Phase 0 — bring up simulator
# =========================
echo "[${TEST_NAME}] Phase 0: bring up simulator"
cd ./waku-simulator
docker compose up -d
cd ..
echo "[${TEST_NAME}] wait 30s"
sleep 30

# =========================
# Phase 1 — CPU-heavy writers (small msgs, high rate)
# =========================
export NUM_PUBLISHER_NODES=24
export NUM_RECEIVER_NODES=8
export MESSAGE_INTERVAL_MILLIS=10
export MIN_MESSAGE_SIZE=256
export MAX_MESSAGE_SIZE=1024
export START_PUBLISHING_AFTER=10
export NUM_MESSAGES=0

echo "[${TEST_NAME}] Phase 1: start writers"
docker run -d --rm --name lpt_cpu \
  -e PUB_NODES=${NUM_PUBLISHER_NODES} \
  -e RCV_NODES=${NUM_RECEIVER_NODES} \
  -e MSG_INTERVAL_MS=${MESSAGE_INTERVAL_MILLIS} \
  -e MIN_MSG=${MIN_MESSAGE_SIZE} \
  -e MAX_MSG=${MAX_MESSAGE_SIZE} \
  -e PUBSUB_TOPIC=${PUBSUB_TOPIC} \
  --network host ${LPT_IMAGE}

# =========================
# Phase 2 — Sonda (exact style from your scripts)
# build image + write env + run with --env-file
# =========================
echo "[${TEST_NAME}] Phase 2: build and start Sonda"
cd ../sonda
docker build -t local-perf-sonda -f ./Dockerfile.sonda .

cat <<EOF > perf-test.env
RELAY_NODE_REST_ADDRESS=http://127.0.0.1:8645
STORE_NODE_REST_ADDRESS=http://127.0.0.1:8644
QUERY_DELAY=0.5
STORE_NODES=/ip4/10.2.0.101/tcp/60001/p2p/16Uiu2HAkyte8uj451tGkbww4Mjcg6DRnmAHxNeWyF4zp23RbpG3n
CLUSTER_ID=66
SHARD=0
EOF

docker run --env-file perf-test.env -l sonda -d --network host local-perf-sonda
cd ../waku-lite/waku-protocol-perf-test

echo "[${TEST_NAME}] hold 12m"
sleep 720

# =========================
# Phase 3 — recovery
# =========================
echo "[${TEST_NAME}] Phase 3: stop writers; observe 120s"
docker kill lpt_cpu || true
sleep 120

# =========================
# Cleanup
# =========================
echo "[${TEST_NAME}] cleanup"
docker kill $(docker ps -q --filter "label=sonda") || true
cd ./waku-simulator
docker compose down -v

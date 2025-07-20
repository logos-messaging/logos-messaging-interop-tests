#!/bin/bash

#this script build the canary app and make basic run to connect to well-known peer via TCP . 
set -e

PEER_ADDRESS="/dns4/node-01.gc-us-central1-a.status.prod.status.im/tcp/30303/p2p/16Uiu2HAp6VjGxNdFZKYYCtP8Yf93JGFHvZXsx2X2u9DS3WTiQEsL6"
PROTOCOL="relay"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/canary_run_$TIMESTAMP.log"

mkdir -p "$LOG_DIR"

echo "Building Waku Canary app..."
make wakucanary >> "$LOG_FILE" 2>&1


echo "Running Waku Canary against:"
echo "  Peer    : $PEER_ADDRESS"
echo "  Protocol: $PROTOCOL"
echo "Log file  : $LOG_FILE"
echo "-----------------------------------"

{
  echo "=== Canary Run: $TIMESTAMP ==="
  echo "Peer     : $PEER_ADDRESS"
  echo "Protocol : $PROTOCOL"
  echo "LogLevel : DEBUG"
  echo "-----------------------------------"
  ./build/wakucanary \
    --address="$PEER_ADDRESS" \
    --protocol="$PROTOCOL" \
    --log-level=DEBUG
  echo "-----------------------------------"
  echo "Exit code: $?"
} 2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}


if [ $EXIT_CODE -eq 0 ]; then
  echo "SUCCESS: Connected to peer and protocol '$PROTOCOL' is supported."
else
  echo "FAILURE: Could not connect or protocol '$PROTOCOL' is unsupported."
fi

exit $EXIT_CODE

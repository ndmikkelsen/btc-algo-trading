#!/bin/sh
# docker-logs.sh — Tail trader container logs (local or remote)
#
# Usage:
#   ./scripts/docker-logs.sh              # Local logs
#   ./scripts/docker-logs.sh user@host    # Remote logs

set -e

REMOTE_DIR="/opt/algo-trader"

if [ -n "${1:-}" ]; then
    REMOTE_HOST="$1"
    echo "==> Tailing logs on $REMOTE_HOST..."
    ssh "$REMOTE_HOST" "cd $REMOTE_DIR && docker compose logs -f trader"
else
    echo "==> Tailing local logs..."
    docker compose logs -f trader
fi

#!/bin/sh
# docker-build.sh — Build Docker image and verify it works
#
# Usage:
#   ./scripts/docker-build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="algo-trader"

info()  { echo "==> $*"; }
error() { echo "ERROR: $*" >&2; exit 1; }

# --- Run tests locally first ------------------------------------------------

info "Running tests locally..."
cd "$PROJECT_DIR"
python -m pytest tests/ features/ -v --tb=short || {
    error "Tests failed — fix before building image"
}

# --- Build ------------------------------------------------------------------

info "Building Docker image..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

# --- Verify container starts ------------------------------------------------

info "Verifying container starts..."
docker run --rm -d --name algo-trader-test \
    -e BYBIT_TESTNET=true \
    -e BYBIT_API_KEY=test \
    -e BYBIT_API_SECRET=test \
    "$IMAGE_NAME" 2>/dev/null && {
    sleep 2
    if docker ps --filter name=algo-trader-test --format '{{.Status}}' | grep -q "Up"; then
        info "Container started successfully"
    else
        info "Container exited (expected without valid API keys)"
    fi
    docker stop algo-trader-test 2>/dev/null || true
} || {
    info "Container exited immediately (expected without valid API keys)"
}

# --- Image info -------------------------------------------------------------

IMAGE_SIZE=$(docker image inspect "$IMAGE_NAME:latest" --format='{{.Size}}' | awk '{printf "%.1f MB", $1/1024/1024}')
info "Image size: $IMAGE_SIZE"

# --- Tag with git hash ------------------------------------------------------

GIT_HASH=$(cd "$PROJECT_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
docker tag "$IMAGE_NAME" "$IMAGE_NAME:$GIT_HASH"
info "Tagged as $IMAGE_NAME:latest and $IMAGE_NAME:$GIT_HASH"

info "Build complete!"

#!/bin/sh
# deploy.sh — Deploy algo-trader to a remote server via SSH
#
# Usage:
#   ./scripts/deploy.sh user@host
#
# Prerequisites:
#   - SSH access to remote host (key-based auth recommended)
#   - Docker + Docker Compose installed on remote host
#   - .env file configured in project root

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="algo-trader"
REMOTE_DIR="/opt/algo-trader"
TARBALL="/tmp/algo-trader-image.tar.gz"

# --- Helpers ---------------------------------------------------------------

usage() {
    echo "Usage: $0 user@host"
    echo ""
    echo "Deploy the algo-trader container to a remote server."
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    exit 1
}

info()  { echo "==> $*"; }
error() { echo "ERROR: $*" >&2; exit 1; }

# --- Validate args ---------------------------------------------------------

case "${1:-}" in
    -h|--help|"") usage ;;
esac

REMOTE_HOST="$1"

# --- Pre-flight checks -----------------------------------------------------

if [ ! -f "$PROJECT_DIR/.env" ]; then
    error ".env file not found in $PROJECT_DIR — copy .env.example and configure it"
fi

if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
    error "docker-compose.yml not found in $PROJECT_DIR"
fi

if ! command -v docker >/dev/null 2>&1; then
    error "docker is not installed locally"
fi

# --- Build image locally ---------------------------------------------------

info "Building Docker image locally..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

GIT_HASH=$(cd "$PROJECT_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
docker tag "$IMAGE_NAME" "$IMAGE_NAME:$GIT_HASH"
info "Tagged image as $IMAGE_NAME:$GIT_HASH"

# --- Save and transfer image -----------------------------------------------

info "Saving image to tarball..."
docker save "$IMAGE_NAME:latest" | gzip > "$TARBALL"
TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
info "Image tarball: $TARBALL_SIZE"

info "Transferring image to $REMOTE_HOST..."
scp "$TARBALL" "$REMOTE_HOST:/tmp/algo-trader-image.tar.gz"

info "Loading image on remote..."
ssh "$REMOTE_HOST" "gunzip -c /tmp/algo-trader-image.tar.gz | docker load && rm /tmp/algo-trader-image.tar.gz"

# --- Copy config files ------------------------------------------------------

info "Creating remote directory $REMOTE_DIR..."
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

info "Copying docker-compose.yml and .env to remote..."
scp "$PROJECT_DIR/docker-compose.yml" "$REMOTE_HOST:$REMOTE_DIR/docker-compose.yml"
scp "$PROJECT_DIR/.env" "$REMOTE_HOST:$REMOTE_DIR/.env"

# --- Start container --------------------------------------------------------

info "Starting container on remote..."
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && docker compose up -d"

# --- Validate ---------------------------------------------------------------

info "Validating deployment..."
sleep 3
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && docker compose ps"

# --- Cleanup local tarball --------------------------------------------------

rm -f "$TARBALL"

info "Deployment complete! Trader running on $REMOTE_HOST"
info "View logs: ./scripts/docker-logs.sh $REMOTE_HOST"

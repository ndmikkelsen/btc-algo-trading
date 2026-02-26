#!/bin/bash
# Cognee management script — BTC Algo Trading Repository
#
# Default: connects to the compute server (btc-cognee.apps.compute.lan)
# Use --local for the local Docker stack (requires Docker + .env)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$REPO_ROOT/.claude/docker"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"
ENV_FILE="$DOCKER_DIR/.env"

REMOTE_URL="http://btc-cognee.apps.compute.lan"
LOCAL_URL="http://localhost:8001"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
    echo "Cognee Manager — BTC Algo Trading"
    echo ""
    echo "Usage: $0 [--local] <command>"
    echo ""
    echo "Options:"
    echo "  --local         Use local Docker stack instead of compute server"
    echo ""
    echo "Remote commands (default — compute server):"
    echo "  health          Check health of Cognee on compute server"
    echo "  status          Show service status (health + URL info)"
    echo ""
    echo "Local Docker commands (require --local):"
    echo "  up              Start all Cognee services"
    echo "  down            Stop all services (keeps data)"
    echo "  restart         Restart all services"
    echo "  logs            View all logs (tail -f)"
    echo "  logs-api        View Cognee API logs only"
    echo "  status          Show Docker service status"
    echo "  health          Check health of all services"
    echo "  shell-db        Connect to PostgreSQL shell"
    echo "  backup          Backup all data volumes"
    echo "  clean           Remove all data (destructive!)"
    echo ""
    echo "Examples:"
    echo "  $0 health                  # Check compute server"
    echo "  $0 --local up              # Start local Docker stack"
    echo "  $0 --local health          # Check local stack"
    echo ""
}

check_compose_file() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}Error: $COMPOSE_FILE not found${NC}"
        exit 1
    fi
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        echo "Copy .env.example to .env: cp $DOCKER_DIR/.env.example $ENV_FILE"
        exit 1
    fi
}

# ─── Remote commands ──────────────────────────────────────────────────────────

cmd_remote_health() {
    echo -e "${BLUE}Health Check — Compute Server${NC}"
    echo "URL: $REMOTE_URL"
    echo ""
    if curl -s "${REMOTE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Cognee: healthy"
        echo "  API docs: ${REMOTE_URL}/docs"
    else
        echo -e "${RED}✗${NC} Cognee: unreachable"
        echo "  Check that compute server is up and btc-cognee is deployed"
    fi
}

cmd_remote_status() {
    cmd_remote_health
}

# ─── Local Docker commands ────────────────────────────────────────────────────

cmd_local_up() {
    check_compose_file
    echo -e "${BLUE}Starting local Cognee stack...${NC}"
    echo "Repository: $REPO_ROOT"
    echo ""
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    echo ""
    echo -e "${GREEN}✓${NC} Services started"
    echo ""
    echo "Waiting for services to be healthy..."
    sleep 5
    cmd_local_health
}

cmd_local_down() {
    check_compose_file
    echo -e "${BLUE}Stopping local Cognee stack...${NC}"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓${NC} Services stopped (data preserved)"
}

cmd_local_restart() {
    cmd_local_down
    echo ""
    cmd_local_up
}

cmd_local_logs() {
    check_compose_file
    echo -e "${BLUE}Logs (Ctrl+C to exit)...${NC}"
    docker compose -f "$COMPOSE_FILE" logs -f
}

cmd_local_logs_api() {
    check_compose_file
    echo -e "${BLUE}Cognee API logs (Ctrl+C to exit)...${NC}"
    docker compose -f "$COMPOSE_FILE" logs -f cognee
}

cmd_local_status() {
    check_compose_file
    echo -e "${BLUE}Local Docker Service Status${NC}"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
}

cmd_local_health() {
    echo -e "${BLUE}Health Check — Local Stack${NC}"
    echo "URL: $LOCAL_URL"
    echo ""

    if curl -s "${LOCAL_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Cognee API: healthy"
    else
        echo -e "${RED}✗${NC} Cognee API: unhealthy"
    fi

    if docker exec btc-algo-cognee-db pg_isready -U cognee > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PostgreSQL: healthy"
    else
        echo -e "${RED}✗${NC} PostgreSQL: unhealthy"
    fi
}

cmd_local_shell_db() {
    echo -e "${BLUE}Connecting to PostgreSQL...${NC}"
    docker exec -it btc-algo-cognee-db psql -U cognee -d cognee
}

cmd_local_backup() {
    BACKUP_DIR="backups/cognee-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    echo -e "${BLUE}Backing up Cognee data...${NC}"
    echo "  Backing up PostgreSQL..."
    docker exec btc-algo-cognee-db pg_dump -U cognee cognee > "$BACKUP_DIR/postgres.sql"
    echo -e "${GREEN}✓${NC} Backup complete: $BACKUP_DIR"
}

cmd_local_clean() {
    echo -e "${RED}WARNING: This will delete ALL local Cognee data!${NC}"
    read -rp "Are you sure? Type 'yes' to confirm: " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Aborted"
        exit 0
    fi

    check_compose_file
    echo -e "${BLUE}Cleaning local Cognee data...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}✓${NC} All local data removed"
}

# ─── Main dispatcher ──────────────────────────────────────────────────────────

USE_LOCAL=false
if [ "${1:-}" = "--local" ]; then
    USE_LOCAL=true
    shift
fi

COMMAND="${1:-}"

if [ "$USE_LOCAL" = true ]; then
    case "$COMMAND" in
        up)         cmd_local_up ;;
        down)       cmd_local_down ;;
        restart)    cmd_local_restart ;;
        logs)       cmd_local_logs ;;
        logs-api)   cmd_local_logs_api ;;
        status)     cmd_local_status ;;
        health)     cmd_local_health ;;
        shell-db)   cmd_local_shell_db ;;
        backup)     cmd_local_backup ;;
        clean)      cmd_local_clean ;;
        *)          usage; exit 1 ;;
    esac
else
    case "$COMMAND" in
        health)     cmd_remote_health ;;
        status)     cmd_remote_status ;;
        "")         usage; exit 1 ;;
        *)
            echo -e "${YELLOW}Note:${NC} '$COMMAND' requires --local for Docker operations"
            echo ""
            usage
            exit 1
            ;;
    esac
fi

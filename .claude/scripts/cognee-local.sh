#!/bin/bash
# Cognee local development management script
# Second-Brain Repository - Isolated Instance

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Docker files are in .claude/docker relative to repo root
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$REPO_ROOT/.claude/docker"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"
ENV_FILE="$DOCKER_DIR/.env"
COGNEE_URL="${COGNEE_URL:-http://localhost:8000}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
    echo "Cognee Local Development Manager"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  up              Start all Cognee services"
    echo "  down            Stop all services (keeps data)"
    echo "  restart         Restart all services"
    echo "  logs            View all logs (tail -f)"
    echo "  logs-api        View Cognee API logs only"
    echo "  status          Show service status"
    echo "  health          Check health of all services"
    echo "  shell-db        Connect to PostgreSQL shell"
    echo "  shell-redis     Connect to Redis CLI"
    echo "  shell-neo4j     Connect to Neo4j Cypher shell"
    echo "  backup          Backup all data volumes"
    echo "  clean           Remove all data (destructive!)"
    echo ""
}

check_compose_file() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}Error: $COMPOSE_FILE not found${NC}"
        echo "Expected location: $COMPOSE_FILE"
        echo "Make sure you're running this from the second-brain repository"
        exit 1
    fi
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        echo "Expected location: $ENV_FILE"
        echo "Create .env file with Cognee configuration"
        exit 1
    fi
}

cmd_up() {
    check_compose_file
    echo -e "${BLUE}🚀 Starting Second-Brain Cognee stack...${NC}"
    echo "Repository: $REPO_ROOT"
    echo "Docker files: $DOCKER_DIR"
    echo ""
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    echo ""
    echo -e "${GREEN}✓${NC} Services started"
    echo ""
    echo "Waiting for services to be healthy..."
    sleep 5
    cmd_health
}

cmd_down() {
    check_compose_file
    echo -e "${BLUE}⏹️  Stopping Second-Brain Cognee stack...${NC}"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓${NC} Services stopped (data preserved)"
}

cmd_restart() {
    cmd_down
    echo ""
    cmd_up
}

cmd_logs() {
    check_compose_file
    echo -e "${BLUE}📋 Viewing all logs (Ctrl+C to exit)...${NC}"
    docker compose -f "$COMPOSE_FILE" logs -f
}

cmd_logs_api() {
    check_compose_file
    echo -e "${BLUE}📋 Viewing Cognee API logs (Ctrl+C to exit)...${NC}"
    docker compose -f "$COMPOSE_FILE" logs -f cognee
}

cmd_status() {
    check_compose_file
    echo -e "${BLUE}📊 Service Status${NC}"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
}

cmd_health() {
    echo -e "${BLUE}🏥 Health Check${NC}"
    echo ""
    
    # Check Cognee API
    if curl -s "${COGNEE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Cognee API: healthy"
    else
        echo -e "${RED}✗${NC} Cognee API: unhealthy"
    fi
    
    # Check PostgreSQL
    if docker exec second-brain-cognee-db pg_isready -U cognee > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PostgreSQL: healthy"
    else
        echo -e "${RED}✗${NC} PostgreSQL: unhealthy"
    fi
    
    # Check Redis
    if docker exec second-brain-cognee-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis: healthy"
    else
        echo -e "${RED}✗${NC} Redis: unhealthy"
    fi
    
    # Check Neo4j
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Neo4j: healthy"
    else
        echo -e "${RED}✗${NC} Neo4j: unhealthy"
    fi
}

cmd_shell_db() {
    echo -e "${BLUE}🐘 Connecting to PostgreSQL...${NC}"
    docker exec -it second-brain-cognee-db psql -U cognee -d cognee
}

cmd_shell_redis() {
    echo -e "${BLUE}📦 Connecting to Redis...${NC}"
    docker exec -it second-brain-cognee-redis redis-cli
}

cmd_shell_neo4j() {
    echo -e "${BLUE}🔗 Connecting to Neo4j...${NC}"
    echo "Password: Check .env for COGNEE_NEO4J_PASSWORD"
    docker exec -it second-brain-cognee-neo4j cypher-shell -u neo4j
}

cmd_backup() {
    BACKUP_DIR="backups/cognee-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    echo -e "${BLUE}💾 Backing up Cognee data...${NC}"
    
    # Backup PostgreSQL
    echo "  Backing up PostgreSQL..."
    docker exec second-brain-cognee-db pg_dump -U cognee cognee > "$BACKUP_DIR/postgres.sql"
    
    # Backup Neo4j (export as Cypher)
    echo "  Backing up Neo4j..."
    docker exec second-brain-cognee-neo4j neo4j-admin dump --to=/tmp/neo4j-backup.dump
    docker cp second-brain-cognee-neo4j:/tmp/neo4j-backup.dump "$BACKUP_DIR/neo4j.dump"
    
    echo -e "${GREEN}✓${NC} Backup complete: $BACKUP_DIR"
}

cmd_clean() {
    echo -e "${RED}⚠️  WARNING: This will delete ALL Cognee data!${NC}"
    read -p "Are you sure? Type 'yes' to confirm: " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Aborted"
        exit 0
    fi
    
    check_compose_file
    echo -e "${BLUE}🧹 Cleaning Cognee data...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}✓${NC} All data removed"
}

# Main command dispatcher
case "${1:-}" in
    up)
        cmd_up
        ;;
    down)
        cmd_down
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        cmd_logs
        ;;
    logs-api)
        cmd_logs_api
        ;;
    status)
        cmd_status
        ;;
    health)
        cmd_health
        ;;
    shell-db)
        cmd_shell_db
        ;;
    shell-redis)
        cmd_shell_redis
        ;;
    shell-neo4j)
        cmd_shell_neo4j
        ;;
    backup)
        cmd_backup
        ;;
    clean)
        cmd_clean
        ;;
    *)
        usage
        exit 1
        ;;
esac

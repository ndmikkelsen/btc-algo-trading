#!/bin/bash
set -euo pipefail

# Sync knowledge to Cognee
# BTC Algo Trading Repository
#
# Usage: ./sync-to-cognee.sh [--clear] [dataset]
#   --clear: Delete and recreate dataset before syncing (fresh upload)
#   dataset: specific dataset to sync (optional)
#   If no dataset specified, syncs all datasets

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COGNEE_API="http://localhost:8001/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Get dataset ID by name
get_dataset_id() {
    local dataset_name="$1"
    curl -s "$COGNEE_API/datasets" | \
        python3 -c "import sys, json; datasets = json.load(sys.stdin); match = next((d for d in datasets if d['name'] == '$dataset_name'), None); print(match['id'] if match else '')"
}

# Delete dataset by name
delete_dataset() {
    local dataset_name="$1"
    local dataset_id=$(get_dataset_id "$dataset_name")

    if [ -z "$dataset_id" ]; then
        log_warn "Dataset not found: $dataset_name (will be created on upload)"
        return 0
    fi

    log_info "Deleting dataset: $dataset_name (ID: $dataset_id)"
    curl -s -X DELETE "$COGNEE_API/datasets/$dataset_id" > /dev/null
    log_info "✓ Deleted: $dataset_name"
}

# Check if Cognee is running
check_cognee() {
    if ! curl -s -f "http://localhost:8001/health" > /dev/null 2>&1; then
        log_error "Cognee is not running. Start it with: .claude/scripts/cognee-local.sh up"
        exit 1
    fi
    log_info "Cognee is running"
}

# Upload files to dataset
upload_files() {
    local dataset_name="$1"
    shift
    local files=("$@")

    if [ ${#files[@]} -eq 0 ]; then
        log_warn "No files to upload for dataset: $dataset_name"
        return 0
    fi

    # Clear dataset if --clear flag was set
    if [ "${CLEAR_DATASETS:-false}" = "true" ]; then
        delete_dataset "$dataset_name"
    fi

    log_info "Uploading ${#files[@]} files to $dataset_name"

    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            log_warn "File not found: $file"
            continue
        fi

        filename=$(basename "$file")
        log_info "  → $filename"

        # Upload file to Cognee
        curl -s -X POST "$COGNEE_API/add" \
            -F "data=@$file" \
            -F "datasetName=$dataset_name" > /dev/null
    done

    log_info "Processing dataset: $dataset_name"
    # Cognify using dataset name (not ID)
    curl -s -X POST "$COGNEE_API/cognify" \
        -H "Content-Type: application/json" \
        -d "{\"datasets\": [\"$dataset_name\"]}" > /dev/null

    log_info "✓ Completed: $dataset_name"
}

# Sync knowledge garden (.claude/)
sync_knowledge_garden() {
    log_info "=== Syncing Knowledge Garden ==="

    files=()
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/.claude" -name "*.md" -type f -print0)

    upload_files "btc-knowledge-garden" "${files[@]}"
}

# Sync patterns (.rules/)
sync_patterns() {
    log_info "=== Syncing Patterns ==="

    files=()
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/.rules" -name "*.md" -type f -print0)

    upload_files "btc-patterns" "${files[@]}"
}

# Sync constitution and core docs
sync_constitution() {
    log_info "=== Syncing Constitution ==="

    files=()
    for file in CONSTITUTION.md VISION.md PLAN.md AGENTS.md; do
        if [ -f "$REPO_ROOT/$file" ]; then
            files+=("$REPO_ROOT/$file")
        fi
    done

    upload_files "btc-constitution" "${files[@]}"
}

# Sync trading strategies
sync_strategies() {
    log_info "=== Syncing Trading Strategies ==="

    files=()
    # Strategy Python files
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/strategies" -name "*.py" -type f -print0 2>/dev/null)
    # Strategy documentation
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/strategies" -name "*.md" -type f -print0 2>/dev/null)

    upload_files "btc-strategies" "${files[@]}"
}

# Sync backtest results
sync_backtests() {
    log_info "=== Syncing Backtest Results ==="

    files=()
    # Backtest markdown reports
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/backtests" -name "*.md" -type f -print0 2>/dev/null)
    # Backtest JSON results (if any)
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$REPO_ROOT/backtests" -name "*.json" -type f -print0 2>/dev/null)

    if [ ${#files[@]} -eq 0 ]; then
        log_warn "No backtest files found"
        return 0
    fi
    upload_files "btc-backtests" "${files[@]}"
}

# Main execution
main() {
    cd "$REPO_ROOT"
    check_cognee

    # Parse flags
    CLEAR_DATASETS=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --clear)
                CLEAR_DATASETS=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    export CLEAR_DATASETS

    if [ $# -eq 0 ]; then
        # Sync all datasets
        sync_knowledge_garden
        sync_patterns
        sync_constitution
        sync_strategies
        sync_backtests
        log_info "=== All datasets synced ==="
    else
        # Sync specific dataset
        case "$1" in
            knowledge-garden|garden)
                sync_knowledge_garden
                ;;
            patterns|rules)
                sync_patterns
                ;;
            constitution)
                sync_constitution
                ;;
            strategies)
                sync_strategies
                ;;
            backtests)
                sync_backtests
                ;;
            *)
                log_error "Unknown dataset: $1"
                log_info "Available datasets: knowledge-garden, patterns, constitution, strategies, backtests"
                exit 1
                ;;
        esac
    fi
}

main "$@"

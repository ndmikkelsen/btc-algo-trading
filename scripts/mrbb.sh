#!/usr/bin/env bash
#
# mrbb.sh - Start/stop the MRBB paper trader
#
# Usage:
#   ./scripts/mrbb.sh start [--capital 1000] [--leverage 10] [--timeframe 5m] [--interval 30] [--preset NAME] [--id ID]
#   ./scripts/mrbb.sh stop [--id ID | --all]
#   ./scripts/mrbb.sh status [--id ID]
#
# Start runs in the foreground with colored output in your terminal.
# Logs are also saved automatically by the Python TeeStream to /tmp/.
# Stop the trader with Ctrl-C or `./scripts/mrbb.sh stop --id ID` from another terminal.
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Defaults
CAPITAL=1000
LEVERAGE=10
TIMEFRAME="5m"
INTERVAL=30
PRESET=""
INSTANCE_ID="default"

pidfile_for() {
    echo "$PROJECT_ROOT/.mrbb-${1}.pid"
}

is_running() {
    local pf
    pf="$(pidfile_for "$1")"
    [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null
}

cleanup() {
    rm -f "$(pidfile_for "$INSTANCE_ID")"
}

do_start() {
    # Parse optional flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --capital)   CAPITAL="$2";      shift 2 ;;
            --leverage)  LEVERAGE="$2";     shift 2 ;;
            --timeframe) TIMEFRAME="$2";    shift 2 ;;
            --interval)  INTERVAL="$2";     shift 2 ;;
            --preset)    PRESET="$2";       shift 2 ;;
            --id)        INSTANCE_ID="$2";  shift 2 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    if is_running "$INSTANCE_ID"; then
        PID=$(cat "$(pidfile_for "$INSTANCE_ID")")
        echo "MRBB trader '$INSTANCE_ID' is already running (PID $PID)"
        exit 1
    fi

    echo "Starting MRBB paper trader..."
    echo "  Instance:  $INSTANCE_ID"
    echo "  Capital:   $CAPITAL"
    echo "  Leverage:  $LEVERAGE"
    echo "  Timeframe: $TIMEFRAME"
    echo "  Interval:  ${INTERVAL}s"
    [ -n "$PRESET" ] && echo "  Preset:    $PRESET"
    echo "  Stop:      Ctrl-C or './scripts/mrbb.sh stop --id $INSTANCE_ID' from another terminal"
    echo ""

    # Write PID file and clean up on exit (Ctrl-C, SIGTERM, normal exit)
    trap cleanup EXIT

    # Run in foreground — Python TeeStream handles colored terminal + file logging
    PRESET_FLAG=""
    [ -n "$PRESET" ] && PRESET_FLAG="--preset $PRESET"

    python3 -u "$PROJECT_ROOT/scripts/run_mrbb_trader.py" \
        --dry-run \
        --capital "$CAPITAL" \
        --leverage "$LEVERAGE" \
        --timeframe "$TIMEFRAME" \
        --interval "$INTERVAL" \
        --instance-id "$INSTANCE_ID" \
        $PRESET_FLAG &

    echo $! > "$(pidfile_for "$INSTANCE_ID")"

    # Wait for the python process; forward signals for graceful shutdown
    wait $!
}

do_stop() {
    local stop_all=false
    local target_id="$INSTANCE_ID"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)   target_id="$2"; shift 2 ;;
            --all)  stop_all=true;  shift ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    if $stop_all; then
        local found=false
        for pf in "$PROJECT_ROOT"/.mrbb-*.pid; do
            [ -f "$pf" ] || continue
            found=true
            local iid
            iid="$(basename "$pf" | sed 's/^\.mrbb-//; s/\.pid$//')"
            _stop_instance "$iid"
        done
        if ! $found; then
            echo "No MRBB instances running."
        fi
        return
    fi

    _stop_instance "$target_id"
}

_stop_instance() {
    local iid="$1"
    local pf
    pf="$(pidfile_for "$iid")"

    if ! is_running "$iid"; then
        echo "MRBB trader '$iid' is not running."
        [ -f "$pf" ] && rm "$pf"
        return
    fi

    PID=$(cat "$pf")
    echo "Stopping MRBB trader '$iid' (PID $PID)..."
    kill "$PID"

    # Wait up to 10 seconds for graceful shutdown
    for _ in $(seq 1 10); do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # Force kill if still alive
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$PID"
    fi

    rm -f "$pf"
    echo "Stopped '$iid'."
}

do_status() {
    local target_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)  target_id="$2"; shift 2 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    if [ -n "$target_id" ]; then
        if is_running "$target_id"; then
            PID=$(cat "$(pidfile_for "$target_id")")
            echo "MRBB trader '$target_id' is running (PID $PID)"
        else
            echo "MRBB trader '$target_id' is not running."
            local pf
            pf="$(pidfile_for "$target_id")"
            [ -f "$pf" ] && rm "$pf"
        fi
        return
    fi

    # Show all instances
    local found=false
    for pf in "$PROJECT_ROOT"/.mrbb-*.pid; do
        [ -f "$pf" ] || continue
        local iid
        iid="$(basename "$pf" | sed 's/^\.mrbb-//; s/\.pid$//')"
        if kill -0 "$(cat "$pf")" 2>/dev/null; then
            PID=$(cat "$pf")
            echo "MRBB trader '$iid' is running (PID $PID)"
            found=true
        else
            rm "$pf"
        fi
    done
    if ! $found; then
        echo "No MRBB instances running."
    fi
}

case "${1:-}" in
    start)  shift; do_start "$@" ;;
    stop)   shift; do_stop "$@" ;;
    status) shift; do_status "$@" ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "  start [--capital N] [--leverage N] [--timeframe TF] [--interval S] [--preset NAME] [--id ID]"
        echo "  stop  [--id ID | --all]    Stop a specific instance or all instances"
        echo "  status [--id ID]           Check running instances"
        exit 1
        ;;
esac

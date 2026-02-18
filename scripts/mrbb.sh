#!/usr/bin/env bash
#
# mrbb.sh - Start/stop the MRBB paper trader
#
# Usage:
#   ./scripts/mrbb.sh start [--capital 1000] [--leverage 10] [--timeframe 5m] [--interval 30]
#   ./scripts/mrbb.sh stop
#   ./scripts/mrbb.sh status
#
# Start runs in the foreground with colored output in your terminal.
# Logs are also saved automatically by the Python TeeStream to /tmp/.
# Stop the trader with Ctrl-C or `./scripts/mrbb.sh stop` from another terminal.
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$PROJECT_ROOT/.mrbb.pid"

# Defaults
CAPITAL=1000
LEVERAGE=10
TIMEFRAME="5m"
INTERVAL=30

is_running() {
    [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

cleanup() {
    rm -f "$PIDFILE"
}

do_start() {
    # Parse optional flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --capital)   CAPITAL="$2";    shift 2 ;;
            --leverage)  LEVERAGE="$2";   shift 2 ;;
            --timeframe) TIMEFRAME="$2";  shift 2 ;;
            --interval)  INTERVAL="$2";   shift 2 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    if is_running; then
        PID=$(cat "$PIDFILE")
        echo "MRBB trader is already running (PID $PID)"
        exit 1
    fi

    echo "Starting MRBB paper trader..."
    echo "  Capital:   $CAPITAL"
    echo "  Leverage:  $LEVERAGE"
    echo "  Timeframe: $TIMEFRAME"
    echo "  Interval:  ${INTERVAL}s"
    echo "  Stop:      Ctrl-C or './scripts/mrbb.sh stop' from another terminal"
    echo ""

    # Write PID file and clean up on exit (Ctrl-C, SIGTERM, normal exit)
    trap cleanup EXIT

    # Run in foreground — Python TeeStream handles colored terminal + file logging
    python3 -u "$PROJECT_ROOT/scripts/run_mrbb_trader.py" \
        --dry-run \
        --capital "$CAPITAL" \
        --leverage "$LEVERAGE" \
        --timeframe "$TIMEFRAME" \
        --interval "$INTERVAL" &

    echo $! > "$PIDFILE"

    # Wait for the python process; forward signals for graceful shutdown
    wait $!
}

do_stop() {
    if ! is_running; then
        echo "MRBB trader is not running."
        [ -f "$PIDFILE" ] && rm "$PIDFILE"
        exit 0
    fi

    PID=$(cat "$PIDFILE")
    echo "Stopping MRBB trader (PID $PID)..."
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

    rm -f "$PIDFILE"
    echo "Stopped."
}

do_status() {
    if is_running; then
        PID=$(cat "$PIDFILE")
        echo "MRBB trader is running (PID $PID)"
    else
        echo "MRBB trader is not running."
        [ -f "$PIDFILE" ] && rm "$PIDFILE"
    fi
}

case "${1:-}" in
    start)  shift; do_start "$@" ;;
    stop)   do_stop ;;
    status) do_status ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "  start [--capital N] [--leverage N] [--timeframe TF] [--interval S]"
        echo "  stop     Stop from another terminal"
        echo "  status   Check if trader is running"
        exit 1
        ;;
esac

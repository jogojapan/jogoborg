#!/bin/bash
# Jogoborg Local Testing - Stop Services
# This script stops all locally running Jogoborg services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping Jogoborg services..."
echo ""

# Stop web server
if [ -f "$SCRIPT_DIR/.web_server.pid" ]; then
    WEB_PID=$(cat "$SCRIPT_DIR/.web_server.pid")
    if kill -0 "$WEB_PID" 2>/dev/null; then
        echo "Stopping web server (PID: $WEB_PID)..."
        kill "$WEB_PID" 2>/dev/null || true
        # Wait for graceful shutdown
        sleep 1
        # Force kill if still running
        kill -9 "$WEB_PID" 2>/dev/null || true
        echo "✓ Web server stopped"
    else
        echo "⚠ Web server not running (stale PID file)"
    fi
    rm -f "$SCRIPT_DIR/.web_server.pid"
else
    echo "⚠ Web server PID file not found"
fi

# Stop scheduler
if [ -f "$SCRIPT_DIR/.scheduler.pid" ]; then
    SCHEDULER_PID=$(cat "$SCRIPT_DIR/.scheduler.pid")
    if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
        echo "Stopping scheduler (PID: $SCHEDULER_PID)..."
        kill "$SCHEDULER_PID" 2>/dev/null || true
        # Wait for graceful shutdown
        sleep 1
        # Force kill if still running
        kill -9 "$SCHEDULER_PID" 2>/dev/null || true
        echo "✓ Scheduler stopped"
    else
        echo "⚠ Scheduler not running (stale PID file)"
    fi
    rm -f "$SCRIPT_DIR/.scheduler.pid"
else
    echo "⚠ Scheduler PID file not found"
fi

echo ""
echo "✓ All services stopped"
echo ""

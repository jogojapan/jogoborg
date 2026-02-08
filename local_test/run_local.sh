#!/bin/bash
# Jogoborg Local Testing - Start Services
# This script starts all Jogoborg services locally without Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment configuration
if [ ! -f "$SCRIPT_DIR/env.local" ]; then
    echo "❌ Error: env.local not found"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Source env.local and export all non-comment variables
# This works in both bash and POSIX-compatible shells
while IFS='=' read -r key value; do
    # Skip empty lines
    [ -z "$key" ] && continue
    # Skip comment lines (starting with #)
    case "$key" in \#*) continue ;; esac
    # Trim leading/trailing whitespace from key
    key=$(echo "$key" | xargs)
    # Trim leading whitespace from value (keep trailing for intentional spaces)
    value=$(echo "$value" | sed 's/^[[:space:]]*//') 
    # Export the variable
    export "$key=$value"
done < "$SCRIPT_DIR/env.local"

# Override paths to use local directories (these always take precedence)
export JOGOBORG_CONFIG_DIR="$SCRIPT_DIR/config"
export JOGOBORG_BORGSPACE_DIR="$SCRIPT_DIR/borgspace"
export JOGOBORG_LOG_DIR="$SCRIPT_DIR/logs"
export JOGOBORG_SOURCESPACE_DIR="$SCRIPT_DIR/sourcespace"

# Use Flutter build output if it exists, otherwise fall back to web source directory
if [ -f "$PROJECT_ROOT/build/web/index.html" ]; then
    export JOGOBORG_WEB_DIR="$PROJECT_ROOT/build/web"
else
    export JOGOBORG_WEB_DIR="$PROJECT_ROOT/web"
fi

# Ensure directories exist
mkdir -p "$JOGOBORG_CONFIG_DIR"
mkdir -p "$JOGOBORG_BORGSPACE_DIR"
mkdir -p "$JOGOBORG_LOG_DIR"
mkdir -p "$JOGOBORG_SOURCESPACE_DIR"

# Debug: Show environment variables (remove this after confirming it works)
echo "Environment variables being exported:"
echo "  JOGOBORG_WEB_PASSWORD=$JOGOBORG_WEB_PASSWORD"
echo "  JOGOBORG_CONFIG_DIR=$JOGOBORG_CONFIG_DIR"
echo "  JOGOBORG_WEB_DIR=$JOGOBORG_WEB_DIR"
echo ""echo "=========================================="
echo "Jogoborg Local Testing - Starting Services"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Web Port: $JOGOBORG_WEB_PORT"
echo "  Web URL: $JOGOBORG_URL"
echo "  Web Dir: $JOGOBORG_WEB_DIR"
echo "  Config Dir: $JOGOBORG_CONFIG_DIR"
echo "  Borg Dir: $JOGOBORG_BORGSPACE_DIR"
echo "  Log Dir: $JOGOBORG_LOG_DIR"
echo "  Source Dir: $JOGOBORG_SOURCESPACE_DIR"
echo ""

# Check if services are already running
if [ -f "$SCRIPT_DIR/.web_server.pid" ]; then
    WEB_PID=$(cat "$SCRIPT_DIR/.web_server.pid")
    if kill -0 "$WEB_PID" 2>/dev/null; then
        echo "⚠ Web server already running (PID: $WEB_PID)"
        echo "  Run ./stop_local.sh to stop services first"
        exit 1
    fi
fi

if [ -f "$SCRIPT_DIR/.scheduler.pid" ]; then
    SCHEDULER_PID=$(cat "$SCRIPT_DIR/.scheduler.pid")
    if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
        echo "⚠ Scheduler already running (PID: $SCHEDULER_PID)"
        echo "  Run ./stop_local.sh to stop services first"
        exit 1
    fi
fi

# Create log files
touch "$JOGOBORG_LOG_DIR/web_server.log"
touch "$JOGOBORG_LOG_DIR/scheduler.log"

# Start web server
echo "Starting web server..."
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" python3 scripts/web_server.py > "$JOGOBORG_LOG_DIR/web_server.log" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$SCRIPT_DIR/.web_server.pid"
echo "✓ Web server started (PID: $WEB_PID)"

# Give web server a moment to start
sleep 2

# Start scheduler
echo "Starting scheduler..."
PYTHONPATH="$PROJECT_ROOT" python3 scripts/scheduler.py > "$JOGOBORG_LOG_DIR/scheduler.log" 2>&1 &
SCHEDULER_PID=$!
echo "$SCHEDULER_PID" > "$SCRIPT_DIR/.scheduler.pid"
echo "✓ Scheduler started (PID: $SCHEDULER_PID)"

echo ""
echo "=========================================="
echo "✓ Services Started Successfully"
echo "=========================================="
echo ""

# Check if Flutter build exists
if [ -f "$PROJECT_ROOT/build/web/index.html" ]; then
    echo "Web Interface: (Flutter Build)"
else
    echo "Web Interface: (Development - API Testing Only)"
    echo "  Tip: Build Flutter for full UI testing:"
    echo "       cd $PROJECT_ROOT"
    echo "       flutter build web"
    echo "       Then restart ./run_local.sh"
fi

echo "  URL: $JOGOBORG_URL"
echo "  Username: $JOGOBORG_WEB_USERNAME"
echo "  Password: $JOGOBORG_WEB_PASSWORD"
echo ""
echo "Logs:"
echo "  Web Server: $JOGOBORG_LOG_DIR/web_server.log"
echo "  Scheduler: $JOGOBORG_LOG_DIR/scheduler.log"
echo ""
echo "To view logs in real-time:"
echo "  tail -f $JOGOBORG_LOG_DIR/web_server.log"
echo "  tail -f $JOGOBORG_LOG_DIR/scheduler.log"
echo ""
echo "To stop services:"
echo "  ./stop_local.sh"
echo ""
echo "To reset test data:"
echo "  ./reset_test_data.sh"
echo ""

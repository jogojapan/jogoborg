#!/bin/bash
# Jogoborg Local Testing - Reset Test Data
# This script resets the local test environment to a clean state

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Jogoborg Local Testing - Reset Test Data"
echo "=========================================="
echo ""

# Check if services are running
if [ -f "$SCRIPT_DIR/.web_server.pid" ] || [ -f "$SCRIPT_DIR/.scheduler.pid" ]; then
    echo "❌ Error: Services are still running"
    echo "Please stop services first: ./stop_local.sh"
    exit 1
fi

echo "This will reset:"
echo "  - Database (jogoborg.db)"
echo "  - Borg repositories"
echo "  - All logs"
echo "  - Sample source data"
echo ""
read -p "Are you sure? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo "Resetting test data..."
echo ""

# Remove database
if [ -f "$SCRIPT_DIR/config/jogoborg.db" ]; then
    echo "Removing database..."
    rm -f "$SCRIPT_DIR/config/jogoborg.db"
    echo "✓ Database removed"
fi

# Remove borg repositories
if [ -d "$SCRIPT_DIR/borgspace" ] && [ "$(ls -A "$SCRIPT_DIR/borgspace")" ]; then
    echo "Removing borg repositories..."
    rm -rf "$SCRIPT_DIR/borgspace"/*
    mkdir -p "$SCRIPT_DIR/borgspace"
    touch "$SCRIPT_DIR/borgspace/.gitkeep"
    echo "✓ Borg repositories removed"
fi

# Clear logs
if [ -d "$SCRIPT_DIR/logs" ] && [ "$(ls -A "$SCRIPT_DIR/logs")" ]; then
    echo "Clearing logs..."
    rm -f "$SCRIPT_DIR/logs"/*.log
    touch "$SCRIPT_DIR/logs/.gitkeep"
    echo "✓ Logs cleared"
fi

# Reset sample source data
if [ -d "$SCRIPT_DIR/sourcespace" ]; then
    echo "Resetting sample source data..."
    rm -rf "$SCRIPT_DIR/sourcespace"/*
    mkdir -p "$SCRIPT_DIR/sourcespace/sample_data/nested"
    
    echo "Sample file 1 - This is test data for backup" > "$SCRIPT_DIR/sourcespace/sample_data/file1.txt"
    echo "Sample file 2 - More test data" > "$SCRIPT_DIR/sourcespace/sample_data/file2.txt"
    echo "Nested sample file - In a subdirectory" > "$SCRIPT_DIR/sourcespace/sample_data/nested/file3.txt"
    
    # Create a larger test file for realistic backup testing
    dd if=/dev/zero of="$SCRIPT_DIR/sourcespace/sample_data/large_file.bin" bs=1M count=10 2>/dev/null
    
    touch "$SCRIPT_DIR/sourcespace/.gitkeep"
    echo "✓ Sample source data reset"
fi

echo ""
echo "=========================================="
echo "✓ Test Data Reset Complete"
echo "=========================================="
echo ""
echo "To reinitialize the environment:"
echo "  ./setup.sh"
echo ""
echo "To start services again:"
echo "  ./run_local.sh"
echo ""

#!/bin/bash
# Jogoborg Local Testing Environment Setup
# This script initializes the local testing environment for development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Jogoborg Local Testing Environment Setup"
echo "=========================================="
echo ""

# Check if running in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: Not running in a Python virtual environment"
    echo "   It's recommended to use a virtual environment:"
    echo "   From project root: python3 -m venv venv"
    echo "   Then activate: source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
fi

echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Install required Python packages
echo ""
echo "Installing Python dependencies..."
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    pip3 install -r "$PROJECT_ROOT/requirements.txt"
    echo "✓ Python dependencies installed"
else
    echo "⚠ Warning: requirements.txt not found"
    echo "  Dependencies may not be installed"
fi

# Create directories
echo ""
echo "Creating directory structure..."
mkdir -p "$SCRIPT_DIR/config"
mkdir -p "$SCRIPT_DIR/borgspace"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/sourcespace/sample_data/nested"

echo "✓ Directories created"

# Create .gitkeep files to preserve empty directories
touch "$SCRIPT_DIR/borgspace/.gitkeep"
touch "$SCRIPT_DIR/logs/.gitkeep"
touch "$SCRIPT_DIR/sourcespace/.gitkeep"

# Copy environment template if it doesn't exist
if [ ! -f "$SCRIPT_DIR/env.local" ]; then
    echo ""
    echo "Creating env.local from template..."
    cp "$SCRIPT_DIR/env.local.example" "$SCRIPT_DIR/env.local"
    echo "✓ env.local created"
    echo "  ⚠ Please review and update $SCRIPT_DIR/env.local as needed"
else
    echo ""
    echo "✓ env.local already exists"
fi

# Create sample source data
echo ""
echo "Creating sample source data..."
echo "Sample file 1 - This is test data for backup" > "$SCRIPT_DIR/sourcespace/sample_data/file1.txt"
echo "Sample file 2 - More test data" > "$SCRIPT_DIR/sourcespace/sample_data/file2.txt"
echo "Nested sample file - In a subdirectory" > "$SCRIPT_DIR/sourcespace/sample_data/nested/file3.txt"

# Create a larger test file for realistic backup testing
dd if=/dev/zero of="$SCRIPT_DIR/sourcespace/sample_data/large_file.bin" bs=1M count=10 2>/dev/null
echo "✓ Sample data created (including 10MB test file)"

# Make scripts executable
echo ""
echo "Setting up scripts..."
chmod +x "$SCRIPT_DIR/run_local.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/stop_local.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/reset_test_data.sh" 2>/dev/null || true
echo "✓ Scripts made executable"

# Load environment variables
echo ""
echo "Loading environment configuration..."
source "$SCRIPT_DIR/env.local"

# Set local paths for testing
export JOGOBORG_CONFIG_DIR="$SCRIPT_DIR/config"
export JOGOBORG_BORGSPACE_DIR="$SCRIPT_DIR/borgspace"
export JOGOBORG_LOG_DIR="$SCRIPT_DIR/logs"
export JOGOBORG_SOURCESPACE_DIR="$SCRIPT_DIR/sourcespace"

# Initialize database if needed
echo ""
echo "Initializing database..."
if [ ! -f "$SCRIPT_DIR/config/jogoborg.db" ]; then
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT" JOGOBORG_CONFIG_DIR="$SCRIPT_DIR/config" python3 scripts/init_db.py
    echo "✓ Database initialized"
else
    echo "✓ Database already exists"
fi

# Initialize GPG if needed
echo ""
echo "Initializing GPG encryption..."
if [ ! -f "$SCRIPT_DIR/config/jogoborg.gpg" ]; then
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT" JOGOBORG_CONFIG_DIR="$SCRIPT_DIR/config" JOGOBORG_GPG_PASSPHRASE="$JOGOBORG_GPG_PASSPHRASE" python3 scripts/init_gpg.py
    echo "✓ GPG key initialized"
else
    echo "✓ GPG key already exists"
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review configuration: $SCRIPT_DIR/env.local"
echo "  2. Start services: cd $SCRIPT_DIR && ./run_local.sh"
echo "  3. Access web UI: http://localhost:8080"
echo ""
echo "To reset test data: ./reset_test_data.sh"
echo "To stop services: ./stop_local.sh"
echo ""

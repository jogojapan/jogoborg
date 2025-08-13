#!/bin/bash
set -e

# Default environment variables
export WEB_PORT=${WEB_PORT:-8080}
export WEB_USERNAME=${WEB_USERNAME:-admin}
export WEB_PASSWORD=${WEB_PASSWORD:-changeme}
export GPG_PASSPHRASE=${GPG_PASSPHRASE:-changeme}

# Initialize configuration directory
if [ ! -f "/config/jogoborg.db" ]; then
    echo "Initializing database..."
    python3 /app/scripts/init_db.py
fi

# Generate GPG key if it doesn't exist
if [ ! -f "/config/jogoborg.gpg" ]; then
    echo "Generating GPG key..."
    python3 /app/scripts/init_gpg.py
fi

# Start background services
echo "Starting backup scheduler..."
python3 /app/scripts/scheduler.py &

echo "Starting web server..."
python3 /app/scripts/web_server.py &

# Keep container running
wait
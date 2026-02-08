#!/bin/bash
set -e

# Ensure credential environment variables are properly set and trimmed
# These variables come from docker-compose.yml environment section
export JOGOBORG_WEB_USERNAME="${JOGOBORG_WEB_USERNAME:-admin}"
export JOGOBORG_WEB_PASSWORD="${JOGOBORG_WEB_PASSWORD:-changeme}"
export JOGOBORG_WEB_PORT="${JOGOBORG_WEB_PORT:-8080}"
export JOGOBORG_GPG_PASSPHRASE="${JOGOBORG_GPG_PASSPHRASE:-changeme}"

# Log the configuration (without exposing sensitive values)
echo "Jogoborg Docker Configuration:"
echo "  Web Port: $JOGOBORG_WEB_PORT"
echo "  Web Username: $JOGOBORG_WEB_USERNAME"
echo "  Web Password: (set)"

# Setup Docker socket access if available
if [ -S /var/run/docker.sock ]; then
    echo "Docker socket access configured."
else
    echo "Docker socket not available - Docker commands will not work. You need to map /var/run/docker.sock into the container. See README.md for details on group permissions and SELinux-related caveats."
fi

sed -i "s|JOGOBORG_URL_PLACEHOLDER|${JOGOBORG_URL}|g" /app/build/web/index.html

# Initialize configuration directory and run database migrations
echo "Initializing database and running migrations..."
python3 /app/scripts/init_db.py

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

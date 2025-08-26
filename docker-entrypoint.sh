#!/bin/bash
set -e

# Default environment variables with JOGOBORG_ prefix
export WEB_PORT=${JOGOBORG_WEB_PORT:-8080}
export WEB_USERNAME=${JOGOBORG_WEB_USERNAME:-admin}
export WEB_PASSWORD=${JOGOBORG_WEB_PASSWORD:-changeme}
export GPG_PASSPHRASE=${JOGOBORG_GPG_PASSPHRASE:-changeme}

# Legacy support - check for old variable names and warn
if [ ! -z "$WEB_PORT" ] && [ -z "$JOGOBORG_WEB_PORT" ]; then
    echo "WARNING: WEB_PORT is deprecated, use JOGOBORG_WEB_PORT instead"
    export WEB_PORT=$WEB_PORT
fi

if [ ! -z "$WEB_USERNAME" ] && [ -z "$JOGOBORG_WEB_USERNAME" ]; then
    echo "WARNING: WEB_USERNAME is deprecated, use JOGOBORG_WEB_USERNAME instead"
    export WEB_USERNAME=$WEB_USERNAME
fi

if [ ! -z "$WEB_PASSWORD" ] && [ -z "$JOGOBORG_WEB_PASSWORD" ]; then
    echo "WARNING: WEB_PASSWORD is deprecated, use JOGOBORG_WEB_PASSWORD instead"
    export WEB_PASSWORD=$WEB_PASSWORD
fi

if [ ! -z "$GPG_PASSPHRASE" ] && [ -z "$JOGOBORG_GPG_PASSPHRASE" ]; then
    echo "WARNING: GPG_PASSPHRASE is deprecated, use JOGOBORG_GPG_PASSPHRASE instead"
    export GPG_PASSPHRASE=$GPG_PASSPHRASE
fi

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

# Build stage - compile the Svelte web frontend
FROM node:22-alpine AS frontend

WORKDIR /app

COPY webui/package.json webui/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY webui/ .
RUN npm run build

# Runtime stage - Ubuntu with Python and backend services
FROM ubuntu:24.04

# Install system dependencies with explicit apt configuration
RUN apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    python3 \
    borgbackup \
    gnupg \
    sqlite3 \
    postgresql-client \
    mariadb-client \
    python3-pip \
    psmisc \
    procps \
    cron \
    ca-certificates \
    sudo \
    apt-transport-https \
    lsb-release \
    time \
    && rm -rf /var/lib/apt/lists/*

# Add PostgreSQL official repository and install postgresql-client-18
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y --no-install-recommends postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
RUN mkdir -p /app

WORKDIR /app

# Copy compiled web frontend from the frontend stage. This is the default
# JOGOBORG_WEB_DIR used by web_server.py.
COPY --from=frontend /app/dist /app/build/web

# Copy application source code
COPY . .

# Install Python dependencies for backend services
RUN pip3 install --break-system-packages \
    awscli \
    cryptography \
    requests \
    croniter

# Create required directories
RUN mkdir -p /sourcespace /borgspace /config /log

# Set up entrypoint and health check
COPY docker-entrypoint.sh /usr/local/bin/
COPY health-check.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /usr/local/bin/health-check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Expose configurable port
EXPOSE ${JOGOBORG_WEB_PORT:-8080}

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
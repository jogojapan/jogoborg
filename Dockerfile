# Build stage - compile Flutter web application
FROM ubuntu:24.04 AS builder

# Install Flutter build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for Flutter
RUN useradd -m -s /bin/bash flutter && \
    echo 'flutter ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Create app directory with proper ownership
RUN mkdir -p /app && chown -R flutter:flutter /app

USER flutter

# Install Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable /home/flutter/flutter
ENV PATH="/home/flutter/flutter/bin:${PATH}"

# Configure Flutter and pre-cache web
RUN flutter config --enable-web --no-analytics && \
    flutter precache --web

WORKDIR /app
COPY --chown=flutter:flutter pubspec.yaml ./
RUN flutter pub get

COPY --chown=flutter:flutter . .
# Use full main application
RUN mv lib/main.dart lib/main_simple.dart || true && \
    mv lib/main_full.dart lib/main.dart || true

# Build Flutter web application
RUN flutter build web --release

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
    rclone \
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

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
RUN mkdir -p /app

WORKDIR /app

# Copy compiled Flutter web assets from builder
COPY --from=builder /app/build/web /app/build/web

# Copy application source code
COPY . .

# Install Python dependencies for backend services
RUN pip3 install --break-system-packages \
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
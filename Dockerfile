FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    borgbackup \
    rclone \
    gnupg \
    sqlite3 \
    postgresql-client \
    mariadb-client \
    python3 \
    python3-pip \
    psmisc \
    procps \
    cron \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"

# Pre-download Flutter dependencies
RUN flutter doctor
RUN flutter config --enable-web

# Create app directory
WORKDIR /app

# Copy Flutter project files
COPY pubspec.yaml ./
RUN flutter pub get

# Copy application source code
COPY . .

# Build Flutter web application
RUN flutter build web --release

# Install Python dependencies for backend services
RUN pip3 install \
    cryptography \
    psutil \
    requests \
    croniter

# Create required directories
RUN mkdir -p /sourcespace /borgspace /config /log

# Set up entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${WEB_PORT:-8080}/health || exit 1

# Expose configurable port
EXPOSE ${WEB_PORT:-8080}

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
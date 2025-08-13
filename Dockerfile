FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libgconf-2-4 \
    gdb \
    libstdc++6 \
    libglu1-mesa \
    fonts-droid-fallback \
    lib32stdc++6 \
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
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for Flutter
RUN useradd -m -s /bin/bash flutter && \
    echo 'flutter ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Install Flutter as non-root user
USER flutter
WORKDIR /home/flutter

# Install Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable flutter
ENV PATH="/home/flutter/flutter/bin:${PATH}"

# Pre-download Flutter dependencies and configure
RUN flutter config --enable-web --no-analytics
RUN flutter precache --web

# Create app directory and set permissions
USER root
RUN mkdir -p /app && chown -R flutter:flutter /app

USER flutter
WORKDIR /app

# Copy Flutter project files (as root first, then change ownership)
USER root
COPY pubspec.yaml ./
RUN chown flutter:flutter pubspec.yaml

USER flutter
RUN flutter pub get

# Copy application source code
USER root
COPY . .
RUN chown -R flutter:flutter /app

USER flutter
# Use simplified main for initial build
RUN mv lib/main.dart lib/main_full.dart || true
RUN mv lib/main_simple.dart lib/main.dart || true

# Build Flutter web application
RUN flutter build web --release

# Switch back to root for final setup
USER root

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
    CMD curl -f http://localhost:${JOGOBORG_WEB_PORT:-8080}/health || exit 1

# Expose configurable port
EXPOSE ${JOGOBORG_WEB_PORT:-8080}

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
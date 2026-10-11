# Build stage - compile the Svelte web frontend
FROM node:22-alpine AS frontend

# Version metadata for the sidebar badge. .git is not in the image, so these
# are passed at build time from the host checkout; defaults are empty and
# version.mjs falls back to 'dev'/'unknown'.
ARG GIT_TAG=
ARG GIT_COMMIT=
ARG BUILD_DATE=
ENV GIT_TAG=$GIT_TAG GIT_COMMIT=$GIT_COMMIT BUILD_DATE=$BUILD_DATE

WORKDIR /app

COPY webui/package.json webui/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY webui/ .
RUN npm run build

# Runtime stage - Ubuntu (26.04 LTS "resolute" for newer deps) + Python backend
FROM ubuntu:26.04

# The ubuntu:26.04 base image bakes in Canonical's /usr/bin/pebble (a static Go
# service-manager binary) which is untracked by dpkg and unused by Jogoborg, but
# ships compiled with the vulnerable go1.26.7 stdlib. Remove it so that Go
# stdlib finding does not appear in the image. (/bin is a symlink to /usr/bin.)
RUN rm -f /usr/bin/pebble /bin/pebble

# Install system dependencies with explicit apt configuration. Trimmed: no
# python3-pip (deps are installed via uv), no psmisc/procps (nothing uses
# ps/fuser/killall), no sqlite3 CLI (Python uses the stdlib module), no
# apt-transport-https (Ubuntu >=22.04 has native https). gnupg + lsb-release
# are kept for the apt repo setups below (PGDG + Docker).
RUN apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    python3 \
    borgbackup \
    gnupg \
    postgresql-client \
    mariadb-client \
    ca-certificates \
    lsb-release \
    time \
    && rm -rf /var/lib/apt/lists/*

# Add PostgreSQL official repository and install postgresql-client-18
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y --no-install-recommends postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (used by job pre/post commands to run `docker stop/exec/…`).
# The Docker CLI is a statically-linked Go binary; its bundled Go stdlib is
# what image scanners flag, and Docker's apt packages are NOT all built with the
# same Go:
#   - Pin docker-ce-cli to 29.9.0 (the first release built with Go 1.26.9, which
#     fixes two Go 1.26.8 stdlib CVEs; verified by inspecting the .deb).
#   - Add --no-install-recommends so the buildx/compose *plugins* are NOT pulled
#     in: the latest docker-buildx-plugin (0.38.0) still bundles Go 1.26.8
#     (verified), so installing them reintroduces the exact CVEs we are clearing.
#     The base `docker` CLI is enough for job pre/post `docker` commands.
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli=5:29.9.0-1~ubuntu.26.04~resolute \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
RUN mkdir -p /app

WORKDIR /app

# Copy compiled web frontend from the frontend stage. This is the default
# JOGOBORG_WEB_DIR used by web_server.py.
COPY --from=frontend /app/dist /app/build/web

# Copy only the backend source + project metadata (not dev/test data, venvs).
COPY scripts/ /app/scripts/
COPY pyproject.toml uv.lock /app/

# Install Python dependencies with uv, pinned to uv.lock for deterministic
# versions. uv is a Rust binary; it is removed again so it is NOT shipped (and
# introduces no Go-stdlib CVEs). --system --break-system-packages mirrors the
# previous pip3 --break-system-packages against Ubuntu's python.
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
RUN cd /app \
    && uv export --frozen -o /tmp/requirements.lock.txt \
    && uv pip install --system --break-system-packages --no-cache -r /tmp/requirements.lock.txt \
    && rm -f /usr/local/bin/uv /tmp/requirements.lock.txt

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
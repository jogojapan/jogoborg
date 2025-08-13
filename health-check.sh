#!/bin/bash

# Health check script that respects JOGOBORG_WEB_PORT at runtime
PORT=${JOGOBORG_WEB_PORT:-8080}
curl -f "http://localhost:${PORT}/health" || exit 1
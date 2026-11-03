#!/usr/bin/env bash

set -e

DEFAULT_MODULE_NAME=src.main

MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}
LOG_CONFIG=${LOG_CONFIG:-/home/fastAPI-Playground/logging.ini}
WORKERS=${WORKERS:-1}
RELOAD=${RELOAD:-true}  # 기본값을 true로 설정

echo "Starting server with:"
echo "- Workers: $WORKERS"
echo "- Reload: ${RELOAD}"
echo "- Host: $HOST"
echo "- Port: $PORT"

# Start Uvicorn with live reload
exec uvicorn \
    "$APP_MODULE" \
    --workers $WORKERS \
    --reload \
    --reload-dir src \
    --proxy-headers \
    --host $HOST \
    --port $PORT \
    --log-config $LOG_CONFIG
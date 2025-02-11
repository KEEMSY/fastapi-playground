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
WORKERS=${WORKERS:-1} # reload 모드에서는 1개의 워커만 사용
RELOAD="--reload"

echo "Starting server with:"
echo "- Workers: $WORKERS"
echo "- Reload: $RELOAD"
echo "- Host: $HOST"
echo "- Port: $PORT"

# RELOAD가 true일 때만 --reload 옵션 추가
if [ "$RELOAD" = "true" ]; then
    RELOAD_OPT="--reload"
else
    RELOAD_OPT=""
fi

# Start Uvicorn with live reload
exec uvicorn \
    "$APP_MODULE" \
    --workers $WORKERS \
    $RELOAD_OPT \
    --proxy-headers \
    --host $HOST \
    --port $PORT \
    --log-config $LOG_CONFIG
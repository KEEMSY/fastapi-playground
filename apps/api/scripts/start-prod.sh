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

# 프로덕션 설정
# CPU 코어 수를 기반으로 워커 수 설정 (코어당 2개의 워커)
# WORKERS=${WORKERS:-$(( $(nproc) * 2 ))}
WORKERS=${WORKERS:=2}  # WORKERS가 설정되지 않았을 경우 2를 기본값으로 사용
RELOAD=""  # 프로덕션에서는 리로드 비활성화2

echo "Starting production server with:"
echo "- Workers: $WORKERS (based on CPU cores: $(nproc))"
echo "- Host: $HOST"
echo "- Port: $PORT"
echo "- Log Level: $LOG_LEVEL"

# Run database migrations
# echo "Running database migrations..."
# echo "1. Checking current migration status..."
# alembic current

# echo "2. Downgrading all migrations..."
# alembic downgrade base || true  # 실패해도 계속 진행

# echo "3. Removing existing migration files..."
# rm -f alembic/versions/*.py || true  # 실패해도 계속 진행

# echo "4. Creating new migration..."
# alembic revision --autogenerate -m "create initial tables"

# echo "5. Upgrading to latest migration..."
# alembic upgrade head

# Start Uvicorn
exec uvicorn \
    "$APP_MODULE" \
    --workers $WORKERS \
    --proxy-headers \
    --host $HOST \
    --port $PORT \
    --log-config $LOG_CONFIG 
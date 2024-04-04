#!/usr/bin/env zsh

# 스크립트의 명령을 실행하다가 중간에 실패하는 경우, 더 이상 진행하지 않도록 함
set -euo pipefail
export COLOR_GREEN='\e[0;32m'
export COLOR_NC='\e[0m' # No Color

echo Run black
black src tests

echo Run Ruff
ruff check src --fix

echo "Run tests"
pytest
echo "${COLOR_GREEN}You are good to go!${COLOR_NC}"
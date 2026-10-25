#!/bin/sh
# Finder entry point. Uses only the existing project-local Python environment.
set -u
DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
PYTHON="$DEMO_DIR/../backend/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo 'SCENT MATCH: 기존 web/backend/.venv/bin/python이 없습니다. 설치하지 않고 중단합니다.'
  if [ -t 0 ]; then read -r _answer; fi
  exit 1
fi
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$DEMO_DIR/manager.py" start "$@"
result=$?
if [ "$result" -ne 0 ] && [ -t 0 ]; then
  echo '안내를 확인한 뒤 Enter를 누르세요.'; read -r _answer
fi
exit "$result"

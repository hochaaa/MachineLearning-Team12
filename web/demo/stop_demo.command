#!/bin/sh
# Never kills an unowned or identity-mismatched process.
set -u
DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
PYTHON="$DEMO_DIR/../backend/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo 'SCENT MATCH: 기존 Python 환경이 없습니다. 임의로 프로세스를 종료하지 않습니다.'
  exit 1
fi
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$DEMO_DIR/manager.py" stop "$@"

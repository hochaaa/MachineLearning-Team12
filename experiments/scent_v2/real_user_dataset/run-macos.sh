#!/bin/sh
# Portable repository-relative entry point; no installs, no existing service edits.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
cd "$PROJECT_DIR"
PYTHON_BIN=${SCENT_COLLECTION_PYTHON:-"$PROJECT_DIR/deployment/final_v1/.local/venv/bin/python"}
if [ ! -x "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3; else echo 'Python 3.10+가 필요합니다. SCENT_COLLECTION_PYTHON을 설정해 주세요.' >&2; exit 1; fi
fi
export PYTHONDONTWRITEBYTECODE=1
if [ "$#" -eq 0 ]; then set -- start; fi
exec "$PYTHON_BIN" -B -m experiments.scent_v2.real_user_dataset.app "$@"

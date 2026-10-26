#!/bin/sh
# Local Frozen V1 install/check/start launcher. Invoke with sh; no chmod needed.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
if ! command -v python3.12 >/dev/null 2>&1; then
  echo 'Python 3.12 is required. Install it, reopen terminal, and retry.' >&2
  exit 2
fi
exec python3.12 -B deployment/final_v1/manage.py "$@"

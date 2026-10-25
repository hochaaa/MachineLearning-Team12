#!/bin/sh
# Future hosting only, after rights/access approval. Does not upload or deploy.
set -eu
cd "$(dirname "$0")/../.."
: "${PORT:?Hosting platform must provide PORT}"
: "${WEB_CORS_ORIGINS:?Set exact approved HTTPS frontend origins}"
export PYTHONDONTWRITEBYTECODE=1
exec "${PYTHON_BIN:-python}" -B -m uvicorn web.backend.production:create_app --factory \
  --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log --no-proxy-headers \
  --limit-concurrency 16 --timeout-keep-alive 5

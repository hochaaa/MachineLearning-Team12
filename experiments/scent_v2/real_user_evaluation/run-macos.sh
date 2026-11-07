#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
export PYTHONPATH=src
export PYTHONDONTWRITEBYTECODE=1
exec deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_user_evaluation.app "$@"

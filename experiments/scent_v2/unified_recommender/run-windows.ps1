param([int]$Port=8023)
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '../../..')
$env:PYTHONPATH='src';$env:PYTHONDONTWRITEBYTECODE='1'
& deployment/final_v1/.local/venv/Scripts/python.exe -B -m experiments.scent_v2.unified_recommender.app --port $Port

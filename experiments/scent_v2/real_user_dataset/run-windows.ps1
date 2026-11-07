# Standard-library runtime only. Windows execution is not yet verified.
param([string]$Command='start',[int]$Port=8014)
$ErrorActionPreference='Stop'
$ProjectDir=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Set-Location $ProjectDir
$PythonBin=$env:SCENT_COLLECTION_PYTHON
if (-not $PythonBin) {
  $LocalPython=Join-Path $ProjectDir 'deployment/final_v1/.local/venv/Scripts/python.exe'
  if (Test-Path $LocalPython) {$PythonBin=$LocalPython} else {$PythonBin='python'}
}
$env:PYTHONDONTWRITEBYTECODE='1'
& $PythonBin -B -m experiments.scent_v2.real_user_dataset.app $Command --port $Port
exit $LASTEXITCODE

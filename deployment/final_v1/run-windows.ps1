# Local Frozen V1 install/check/start; no policy bypass, elevation or shared venv.
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error 'Python launcher missing. Install Python 3.12 and reopen PowerShell.'
    exit 2
}
& py -3.12 -B deployment/final_v1/manage.py @args
exit $LASTEXITCODE

param([string]$Command='start',[string]$Policy='',[int]$Port=8021)
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '../../..')
$env:PYTHONPATH='src';$env:PYTHONDONTWRITEBYTECODE='1'
$Py='deployment/final_v1/.local/venv/Scripts/python.exe'
if (!(Test-Path $Py)) { throw 'Existing Python environment missing; follow local setup documentation. No automatic install.' }
$ArgsList=@('-B','-m','experiments.scent_v2.real_user_evaluation.app',$Command,'--port',"$Port")
if ($Policy) { $ArgsList+=@('--policy',$Policy) }
& $Py @ArgsList

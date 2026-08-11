# Launch FinWise desktop app (Flet).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$flet = "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts\flet.exe"
if (-not (Test-Path $flet)) {
    $flet = (Get-Command flet -ErrorAction SilentlyContinue).Source
}
if (-not $flet) {
    Write-Host "flet CLI not found. Run: python -m pip install -U flet[all]" -ForegroundColor Red
    exit 1
}

& $flet run main.py

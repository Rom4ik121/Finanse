# Build Finanse APK on Windows (PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$flutter = "$env:USERPROFILE\flutter\3.44.8"
if (-not (Test-Path "$flutter\bin\flutter.bat")) {
    $flutter = "C:\flutter"
}
$env:FLUTTER_ROOT = $flutter
$env:PATH = "$flutter\bin;" + $env:PATH
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME

$flet = "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts\flet.exe"
if (-not (Test-Path $flet)) {
    $flet = (Get-Command flet -ErrorAction SilentlyContinue).Source
}
if (-not $flet) {
    Write-Host "flet CLI not found. Run: python -m pip install -U flet[all]" -ForegroundColor Red
    exit 1
}

Write-Host "Flutter: $flutter" -ForegroundColor Cyan
Write-Host "Android SDK: $env:ANDROID_HOME" -ForegroundColor Cyan
Write-Host "Building APK (first run may take 20-40 min)..." -ForegroundColor Yellow

python -m pip install -U "flet[all]" -r requirements.txt -q

& $flet build apk `
    --org com.finanse.app `
    --product FinWise `
    --build-version 0.1.0 `
    --build-number 1 `
    --yes `
    --no-rich-output `
    -v

$apk = Get-ChildItem -Path build -Recurse -Filter "*.apk" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($apk) {
    Write-Host ""
    Write-Host "APK ready: $($apk.FullName)" -ForegroundColor Green
} else {
    Write-Host "Build finished but APK not found under build/" -ForegroundColor Yellow
    Get-ChildItem build -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
}

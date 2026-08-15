# Create FinWise shortcut on the Windows desktop with the app icon.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$IconPath = Join-Path $ProjectRoot "assets\icon.ico"
$Launcher = Join-Path $ProjectRoot "scripts\launch_finwise.bat"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "FinWise.lnk"

if (-not (Test-Path $IconPath)) {
    Write-Host "Icon not found: $IconPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $Launcher)) {
    Write-Host "Launcher not found: $Launcher" -ForegroundColor Red
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $Launcher
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.IconLocation = "$IconPath,0"
$shortcut.Description = "FinWise personal finance tracker"
$shortcut.Save()

Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $ShortcutPath"

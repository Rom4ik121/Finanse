# Publish Finanse to GitHub (run once from project root in PowerShell).
# Requires: GitHub CLI — https://cli.github.com/

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== Finanse → GitHub ===" -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI: winget install GitHub.cli" -ForegroundColor Yellow
    exit 1
}

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Log in to GitHub (browser will open)..." -ForegroundColor Yellow
    gh auth login -h github.com -p https -w
}

$owner = (gh api user -q .login)
Write-Host "GitHub user: $owner"

$defaultName = "finanse"
$repoName = Read-Host "Repository name [$defaultName]"
if ([string]::IsNullOrWhiteSpace($repoName)) { $repoName = $defaultName }

$visibility = Read-Host "Visibility public/private [private]"
if ([string]::IsNullOrWhiteSpace($visibility)) { $visibility = "private" }
$isPrivate = $visibility -ne "public"

if (git remote get-url origin 2>$null) {
    Write-Host "Remote origin already set. Pushing..."
    git push -u origin main
} else {
    if ($isPrivate) {
        gh repo create $repoName --private --source=. --remote=origin --push
    } else {
        gh repo create $repoName --public --source=. --remote=origin --push
    }
}

$url = "https://github.com/$owner/$repoName"
Write-Host ""
Write-Host "Done: $url" -ForegroundColor Green
Write-Host "Next: open Codemagic → Add application → select this repo → workflow ios-ipa"

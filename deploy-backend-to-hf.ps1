# Deploys the backend folder to a Hugging Face Space (Docker SDK).
#
# PREREQUISITES (do these once on huggingface.co):
#   1. Create a free account.
#   2. Create a new Space:  SDK = Docker,  blank template,  Public.
#   3. Create a Write access token:  Settings -> Access Tokens -> New token.
#
# USAGE (run in PowerShell):
#   ./deploy-backend-to-hf.ps1 -User <hf-username> -Space <space-name>
#
# When git asks for a password during push, paste your Write token.

param(
    [Parameter(Mandatory = $true)] [string]$User,
    [Parameter(Mandatory = $true)] [string]$Space
)

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "backend"
$work    = Join-Path $env:TEMP "hf-deploy-$Space"

Write-Host "==> Cloning Space repo..." -ForegroundColor Cyan
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
git clone "https://huggingface.co/spaces/$User/$Space" $work

Write-Host "==> Copying backend files (excluding venv, db, caches)..." -ForegroundColor Cyan
$exclude = @("venv", ".venv", "__pycache__", "attendance.db", ".env")
Get-ChildItem -Path $backend -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $work -Recurse -Force
}
# Remove any nested __pycache__ that slipped through
Get-ChildItem -Path $work -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

Write-Host "==> Committing and pushing..." -ForegroundColor Cyan
Push-Location $work
git add .
git commit -m "Deploy attendance API"
git push
Pop-Location

Write-Host ""
Write-Host "Done. Your API will build at:" -ForegroundColor Green
Write-Host "  https://$User-$Space.hf.space" -ForegroundColor Green
Write-Host "Build takes ~10-15 min the first time (TensorFlow). Watch the 'Logs' tab on the Space." -ForegroundColor Yellow

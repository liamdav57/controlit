# UPLOAD_TO_GITHUB.ps1 - Push source code and trigger cloud EXE build

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  ControlIt - Upload to GitHub" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

Set-Location $PSScriptRoot

# Step 1: Push any source changes
Write-Host "`n[1/3] Pushing source code to GitHub..." -ForegroundColor Yellow
git add -A
$status = git status --porcelain
if ($status) {
    git commit -m "Update source code"
    git push
    Write-Host "OK - Source pushed" -ForegroundColor Green
} else {
    Write-Host "OK - Nothing new to push" -ForegroundColor Green
}

# Step 2: Check GitHub CLI
Write-Host "`n[2/3] Checking GitHub CLI..." -ForegroundColor Yellow
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
    winget install --id GitHub.cli -e --silent --accept-package-agreements --accept-source-agreements
    Write-Host "Please CLOSE this window and run again." -ForegroundColor Red
    pause
    exit
}
$loginCheck = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    gh auth login --web --hostname github.com -p https
}
Write-Host "OK" -ForegroundColor Green

# Step 3: Trigger cloud build
Write-Host "`n[3/3] Triggering build on GitHub..." -ForegroundColor Yellow
gh workflow run build.yml --repo liamdav57/controlit
Write-Host "OK - Build started!" -ForegroundColor Green

Write-Host "`n===========================================" -ForegroundColor Green
Write-Host "  SUCCESS!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  GitHub is building your EXE in the cloud."
Write-Host "  Check progress at:"
Write-Host "  https://github.com/liamdav57/controlit/actions" -ForegroundColor Cyan
Write-Host ""

Start-Process "https://github.com/liamdav57/controlit/actions"
pause

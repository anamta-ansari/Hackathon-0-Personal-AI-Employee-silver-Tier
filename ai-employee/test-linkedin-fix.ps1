# LinkedIn Fix - PowerShell Test Script
# Run this in PowerShell to test all fixes

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " LinkedIn Auto-Posting - Fix Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Check session file
Write-Host "STEP 1: Checking session file..." -ForegroundColor Yellow
if (Test-Path "config\linkedin_session.json") {
    Write-Host "[OK] Session file exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Session file NOT found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Running re-authentication..." -ForegroundColor Yellow
    python src\skills\linkedin_session_auth.py login
    exit
}

Write-Host ""

# STEP 2: Validate session cookies
Write-Host "STEP 2: Validating session cookies..." -ForegroundColor Yellow
python src\skills\linkedin_session_simple_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Session validation failed!" -ForegroundColor Red
    Write-Host "Running re-authentication..." -ForegroundColor Yellow
    python src\skills\linkedin_session_auth.py login
    exit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SESSION VALIDATED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# STEP 3: Test manual posting
Write-Host "STEP 3: Testing manual posting..." -ForegroundColor Yellow
Write-Host "This will open a browser and attempt to post to LinkedIn." -ForegroundColor Yellow
Write-Host "Watch the browser window!" -ForegroundColor Yellow
Write-Host ""
pause

python src\skills\linkedin_browser_post.py --content "Test post - verifying memory fixes! #Automation #Testing"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Manual test failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check if browser opened" -ForegroundColor White
    Write-Host "  2. Check if you're logged into LinkedIn" -ForegroundColor White
    Write-Host "  3. Check internet connection" -ForegroundColor White
    Write-Host "  4. Review logs in logs\ folder" -ForegroundColor White
    Write-Host ""
    exit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " MANUAL TEST COMPLETED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If you saw 'Post published successfully', the fixes are working!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart orchestrator: python src\orchestration\orchestrator.py" -ForegroundColor White
Write-Host "  2. Move failed posts to Approved folder" -ForegroundColor White
Write-Host "  3. Watch for successful posting within 60-90 seconds" -ForegroundColor White
Write-Host ""

@echo off
REM LinkedIn Fix - Complete Test Script
REM This tests all the fixes applied to LinkedIn auto-posting

echo ============================================================
echo  LinkedIn Auto-Posting - Fix Verification
echo ============================================================
echo.

echo STEP 1: Checking session file...
if exist "config\linkedin_session.json" (
    echo [OK] Session file exists
) else (
    echo [ERROR] Session file NOT found!
    goto :reauth_required
)

echo.
echo STEP 2: Validating session cookies (simple check)...
python src\skills\linkedin_session_simple_check.py
if errorlevel 1 (
    echo.
    goto :reauth_required
)

echo.
echo ============================================================
echo  SESSION VALIDATED
echo ============================================================
echo.
echo STEP 3: Test manual posting...
echo.
echo This will open a browser and attempt to post to LinkedIn.
echo Watch the browser window!
echo.
pause

python src\skills\linkedin_browser_post.py --content "Test post - verifying memory fixes! #Automation #Testing"

if errorlevel 1 (
    echo.
    echo [ERROR] Manual test failed!
    echo.
    echo Troubleshooting:
    echo   1. Check if browser opened
    echo   2. Check if you're logged into LinkedIn
    echo   3. Check internet connection
    echo   4. Review logs in logs\ folder
    echo.
    goto :end
)

echo.
echo ============================================================
echo  MANUAL TEST COMPLETED
echo ============================================================
echo.
echo If you saw "Post published successfully", the fixes are working!
echo.
echo Next steps:
echo   1. Restart orchestrator: python src\orchestration\orchestrator.py
echo   2. Move failed posts to Approved folder
echo   3. Watch for successful posting within 60-90 seconds
echo.
goto :end

:reauth_required
echo.
echo ============================================================
echo  RE-AUTHENTICATION REQUIRED
echo ============================================================
echo.
echo Your LinkedIn session needs to be refreshed.
echo.
echo Running re-authentication...
python src\skills\linkedin_session_auth.py login

if errorlevel 1 (
    echo.
    echo [ERROR] Re-authentication failed!
    echo Please run manually: python src\skills\linkedin_session_auth.py login
    goto :end
)

echo.
echo [OK] Re-authentication complete!
echo.
echo Now test manual posting:
echo   python src\skills\linkedin_browser_post.py --content "Test post"
echo.

:end
echo.
echo ============================================================
echo  Test Complete
echo ============================================================
pause

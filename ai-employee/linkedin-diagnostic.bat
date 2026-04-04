@echo off
REM LinkedIn Diagnostic and Fix Script
REM This helps diagnose and fix LinkedIn session issues

echo ============================================================
echo  LinkedIn Session Diagnostic
echo ============================================================
echo.

echo Step 1: Checking session file...
if exist "config\linkedin_session.json" (
     echo [OK] Session file exists
) else (
    echo [ERROR] Session file NOT found!
    goto :login_required
)

echo.
echo Step 2: Validating session cookies...
python src\skills\linkedin_session_simple_check.py
if errorlevel 1 (
    echo.
    goto :login_required
)

echo.
echo ============================================================
echo  DIAGNOSIS COMPLETE
echo ============================================================
echo.
echo Your session cookies appear VALID.
echo.
echo If LinkedIn posting is still failing, the issue might be:
echo   1. Playwright memory issues (already fixed)
echo   2. LinkedIn's bot detection blocking automation
echo   3. Session was captured from a different browser profile
echo.
echo Next steps:
echo   1. Stop the orchestrator (Ctrl+C)
echo   2. Run: python src\skills\linkedin_session_auth.py login
echo   3. WAIT for the browser to open and log in COMPLETELY
echo   4. Wait for "SESSION SAVED SUCCESSFULLY" message
echo   5. Move failed posts from Failed/ to Approved/
echo   6. Restart orchestrator
echo.
goto :end

:login_required
echo.
echo ============================================================
echo  RE-AUTHENTICATION REQUIRED
echo ============================================================
echo.
echo Your LinkedIn session has expired or is invalid.
echo.
echo Please run:
echo   python src\skills\linkedin_session_auth.py login
echo.
echo IMPORTANT: 
echo   - A browser window will open
echo   - YOU must log into LinkedIn manually
echo   - Wait for "SESSION SAVED SUCCESSFULLY" message
echo.
pause

:end

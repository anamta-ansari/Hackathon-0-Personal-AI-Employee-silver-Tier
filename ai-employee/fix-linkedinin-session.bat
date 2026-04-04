@echo off
REM LinkedIn Session Fix Script
REM This script helps you quickly re-authenticate LinkedIn

echo ============================================
echo  LinkedIn Session Re-authentication
echo ============================================
echo.
echo This will open a browser for you to log into LinkedIn.
echo After successful login, your session will be saved.
echo.
echo Press Ctrl+C after you see "SESSION SAVED SUCCESSFULLY"
echo to return to the orchestrator.
echo.
pause

cd /d "%~dp0"

echo.
echo Starting LinkedIn authentication...
echo.

python src\skills\linkedin_session_auth.py login

echo.
echo ============================================
echo  Authentication Complete
echo ============================================
echo.
echo Next steps:
echo 1. If login was successful, restart your orchestrator:
echo    python src\orchestration\orchestrator.py
echo.
echo 2. Move failed LinkedIn posts from Failed/ to Approved/
echo    to retry them with the new session.
echo.
pause

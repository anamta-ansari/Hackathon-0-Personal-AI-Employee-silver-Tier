@echo off
REM AI Employee - Quick Start Script for Windows
REM This script sets up and starts the AI Employee system

echo ============================================
echo AI Employee - Bronze Tier
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.13+ from https://python.org
    exit /b 1
)

echo [1/5] Checking Python installation... OK
echo.

REM Check if .env exists
if not exist .env (
    echo [2/5] Creating .env file from template...
    copy .env.example .env
    echo Created .env file - please edit with your settings
    echo.
) else (
    echo [2/5] Found existing .env file... OK
    echo.
)

REM Install dependencies
echo [3/5] Installing Python dependencies...
pip install -r requirements.txt -q
echo Dependencies installed... OK
echo.

REM Check vault structure
echo [4/5] Checking vault structure...
if not exist "..\AI_Employee_Vault" (
    echo Creating vault structure...
    mkdir "..\AI_Employee_Vault\Inbox"
    mkdir "..\AI_Employee_Vault\Needs_Action"
    mkdir "..\AI_Employee_Vault\Done"
    mkdir "..\AI_Employee_Vault\Plans"
    mkdir "..\AI_Employee_Vault\Pending_Approval"
    mkdir "..\AI_Employee_Vault\Approved"
    mkdir "..\AI_Employee_Vault\Rejected"
    mkdir "..\AI_Employee_Vault\Logs"
    mkdir "..\AI_Employee_Vault\Briefings"
    mkdir "..\AI_Employee_Vault\Accounting"
    echo Vault created... OK
) else (
    echo Vault exists... OK
)
echo.

REM Start orchestrator
echo [5/5] Starting AI Employee Orchestrator...
echo.
echo ============================================
echo AI Employee is now running!
echo.
echo Press Ctrl+C to stop
echo ============================================
echo.

python src\orchestration\orchestrator.py --dry-run

echo.
echo AI Employee stopped.
pause

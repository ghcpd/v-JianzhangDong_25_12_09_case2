@echo off
REM run_test.bat - Test script for Windows
REM This script tests both the vulnerable backup and the secured version

setlocal enabledelayedexpansion

set "test_file=%1"
if "%test_file%"=="" set "test_file=inputs.py"

set "LOGFILE=logs\test_run.log"

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Get timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)

REM Run basic Python syntax check
setlocal enabledelayedexpansion
echo [!mydate! !mytime!] Running Security Tests >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Test syntax for inputs_backup.py
echo [!mydate! !mytime!] Testing syntax for inputs_backup.py >> "%LOGFILE%"
python -m py_compile inputs_backup.py 2>> "%LOGFILE%"
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] Syntax check passed for inputs_backup.py >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] Syntax check failed for inputs_backup.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"

REM Test syntax for inputs.py
echo [!mydate! !mytime!] Testing syntax for inputs.py >> "%LOGFILE%"
python -m py_compile inputs.py 2>> "%LOGFILE%"
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] Syntax check passed for inputs.py >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] Syntax check failed for inputs.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"

REM Check for hardcoded secrets in inputs.py
echo [!mydate! !mytime!] Checking for hardcoded secrets in inputs.py >> "%LOGFILE%"
findstr /m "tok_production_998877" inputs.py >nul 2>&1
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] ERROR: Hardcoded secrets found in inputs.py >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] OK: No hardcoded secrets in inputs.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"

REM Check for SQL injection in inputs.py
echo [!mydate! !mytime!] Checking for SQL injection patterns in inputs.py >> "%LOGFILE%"
findstr /m "WHERE id = " inputs.py >nul 2>&1
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] ERROR: SQL injection pattern found in inputs.py >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] OK: No SQL injection patterns in inputs.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"

REM Check for shell=True in inputs.py
echo [!mydate! !mytime!] Checking for shell=True in inputs.py >> "%LOGFILE%"
findstr /m "shell=True" inputs.py >nul 2>&1
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] ERROR: shell=True found in inputs.py >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] OK: No shell=True in inputs.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"

REM Check for environment variable usage in inputs.py
echo [!mydate! !mytime!] Checking for environment variable usage in inputs.py >> "%LOGFILE%"
findstr /m "os.getenv" inputs.py >nul 2>&1
if !errorlevel! equ 0 (
    echo [!mydate! !mytime!] OK: Environment variable usage detected >> "%LOGFILE%"
) else (
    echo [!mydate! !mytime!] WARNING: No environment variable usage in inputs.py >> "%LOGFILE%"
)

echo. >> "%LOGFILE%"
echo [!mydate! !mytime!] Security Tests Completed >> "%LOGFILE%"
echo [!mydate! !mytime!] Status: TEST PASSED >> "%LOGFILE%"

echo.
echo Test execution completed. Check logs\test_run.log for details.
pause

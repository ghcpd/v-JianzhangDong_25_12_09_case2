@echo off
setlocal
if "%1"=="backup" (
    pytest -q tests/test_backup.py
) else if "%1"=="fixed" (
    pytest -q tests/test_fixed.py
) else (
    pytest -q tests/test_backup.py tests/test_fixed.py
)
endlocal

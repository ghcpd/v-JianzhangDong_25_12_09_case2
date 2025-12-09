@echo off
python tests\test_runner.py input_backup.py
python tests\test_runner.py input.py
if %ERRORLEVEL% equ 0 (
  echo All tests passed
) else (
  echo Tests failed
  exit /b 1
)

@echo off
if "%1"=="" (
  set FILE=inputs.py
) else (
  set FILE=%1
)
python -u tests\check_file.py %FILE%
IF %ERRORLEVEL% NEQ 0 (
  EXIT /B 1
)
EXIT /B 0

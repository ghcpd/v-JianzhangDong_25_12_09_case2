# Security Hardened Inputs Repo

This repository contains an audited and secured version of `inputs.py` and supportive files to reproduce, test, and validate the fixes.

## Overview of generated files (✅ essential)

- `inputs_backup.py` — Original file (unaltered) saved as a backup for comparison and tests.
- `inputs.py` — The secured, updated implementation.
- `report.json` — Structured vulnerability findings and fixes for `inputs.py` (detailed, per-vulnerability).
- `tests/check_file.py` — Static checking utility used by the test scripts to detect insecure patterns.
- `run_test.sh` — Linux/macOS test runner: runs `tests/check_file.py` against a target file (default `inputs.py`).
- `run_test.bat` — Windows test runner (uses Python) — same behaviour as the shell script.
- `auto_test.py` — Automatic test orchestrator; detects environment (Windows/Linux/Docker) and runs the appropriate test scripts in sequence for `inputs_backup.py` and `inputs.py`, logging results to `logs/test_run.log`.
- `requirements.txt` — Required Python packages to run these checks.
- `Dockerfile` — Container to build an environment and run `auto_test.py` automatically.
- `setup.sh` — Helper script to create a virtualenv and install dependencies on Linux/macOS.
- `logs/test_run.log` — Generated test runtime log (created when you run `auto_test.py`).

## Setup

Linux / macOS

```bash
# create a python venv and install deps
./setup.sh
source .venv/bin/activate
```

Windows (PowerShell/CMD)

```powershell
# Use your preferred virtual environment setup method and install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Docker

```bash
# Build
docker build -t inputs-security-test .
# Run
docker run --rm inputs-security-test
```

## How to run tests manually

Linux/macOS

```bash
# run checks for inputs.py (default)
./run_test.sh
# run checks for the backup/original
./run_test.sh inputs_backup.py
```

Windows

```powershell
# run tests for default
run_test.bat
# run tests for backup
run_test.bat inputs_backup.py
```

## Automatic test runner (auto_test.py)

`auto_test.py` will detect the environment and run the appropriate runner for both the backup and the fixed file in sequence. It logs all output into `logs/test_run.log` with timestamps and a final status line `TEST PASSED` or `TEST FAILED`.

```bash
python auto_test.py
# Inspect the log
cat logs/test_run.log
```

The script returns `0` when both tests pass (meaning the fixed `inputs.py` did not trigger the static checks) and returns `1` when ANY test fails.

## Interpreting test results

- `TEST PASSED` in `logs/test_run.log` indicates all checks (the minimal static checks) passed for the tested file.
- `TEST FAILED` means one or more checks detected insecure patterns.

> Notes: The included tests are intentionally lightweight static checks to demonstrate the presence/absence of particular insecure patterns. For production, adopt deeper static analysis tools, unit tests, input validation, and runtime checks.

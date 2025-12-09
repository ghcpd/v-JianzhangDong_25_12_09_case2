# Security Audit and Hardening

This repository contains an audited and hardened Flask application along with test harness and environment scripts.

Files generated:

- input_backup.py: Original (vulnerable) application preserved for comparison.
- input.py: Hardened and secure application.
- report.json: Structured report describing vulnerabilities and fixes.
- tests/test_runner.py: Test runner used to validate SQL-injection and other fixes.
- run_test.sh / run_test.bat: Platform-specific test runners.
- auto_test.py: Auto test controller that runs platform script and per-file tests, logs output to logs/test_run.log.
- requirements.txt: Python dependencies.
- Dockerfile: Containerized environment for the application.
- setup.sh: Setup script for Linux/macOS to create venv, install dependencies and initialize DB.
- logs/: Directory where test logs are written.

Setup

Linux / macOS

1. Ensure Python 3.8+ is installed.
2. Run `bash setup.sh` to create a virtualenv, install requirements and initialize the test database.
3. Set required environment variables before running the app:
   - PAYMENT_TOKEN
   - INTERNAL_AUTH_KEY
   - ADMIN_API_KEY
   Optionally: DB_FILE, ALLOWED_NOTIFY_HOSTS, CONFIG_DIR

Windows

1. Install Python 3.8+ and create a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Initialize DB by running `python -c "import sqlite3; ..."` or by using setup.sh in WSL.

Running tests

Linux / macOS

- Run `bash run_test.sh` to execute automated tests for both the vulnerable and fixed versions.

Windows

- Run `run_test.bat` to execute tests.

Auto testing

- Use `python auto_test.py` to automatically detect the platform, run the platform-specific test script and run per-file tests. Logs will be written to `logs/test_run.log` and include timestamps as well as final status lines `TEST PASSED` or `TEST FAILED`.

Interpreting logs

- Each test run includes a TIMESTAMP, OUTPUT, STATUS.
- The final status `TEST PASSED` indicates that the fixed application passed the validation suite and that the vulnerability demonstrated in the backup file was mitigated.

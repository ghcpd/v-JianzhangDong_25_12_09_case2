#!/usr/bin/env bash
set -e
python3 tests/test_runner.py input_backup.py
python3 tests/test_runner.py input.py
echo "All tests passed"

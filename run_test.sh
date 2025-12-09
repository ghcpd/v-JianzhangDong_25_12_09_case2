#!/usr/bin/env bash
set -e
TARGET=$1
export PYTHONPATH=.
# Ensure logs dir
mkdir -p logs
if [ "$TARGET" = "backup" ]; then
  pytest -q tests/test_backup.py
elif [ "$TARGET" = "fixed" ]; then
  pytest -q tests/test_fixed.py
else
  pytest -q tests/test_backup.py tests/test_fixed.py
fi

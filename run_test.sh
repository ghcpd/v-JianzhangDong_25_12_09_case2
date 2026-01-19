#!/usr/bin/env bash
set -euo pipefail
FILE=${1:-inputs.py}
PY=${PYTHON:-python3}
$PY -u tests/check_file.py "$FILE"

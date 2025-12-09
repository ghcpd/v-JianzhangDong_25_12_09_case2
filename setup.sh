#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Prepare database
python - <<'PY'
import sqlite3, os
if os.path.exists('appdata.db'):
    os.remove('appdata.db')
conn = sqlite3.connect('appdata.db')
c = conn.cursor()
c.execute('CREATE TABLE profiles (id TEXT PRIMARY KEY, name TEXT, balance REAL)')
c.execute("INSERT INTO profiles (id,name,balance) VALUES ('1','Alice',100.0)")
c.execute("INSERT INTO profiles (id,name,balance) VALUES ('2','Bob',200.0)")
conn.commit()
conn.close()
PY
mkdir -p configs logs
echo "Setup complete"

import os
import sqlite3
import subprocess
import json
import tempfile
import requests
import importlib
import types
import sys
import pathlib
# Ensure project root is importable when pytest runs from tests/ directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import input_backup as ib

DB = os.path.abspath("appdata.db")


def setup_module(module):
    # create a small database
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, name TEXT, balance REAL)")
    c.execute("DELETE FROM profiles")
    c.execute("INSERT INTO profiles (id,name,balance) VALUES (1, 'Alice', 1000)")
    c.execute("INSERT INTO profiles (id,name,balance) VALUES (2, 'Bob', 250)")
    conn.commit()
    conn.close()


def test_sql_injection_vulnerable():
    res = ib.query_profile("1' OR '1'='1")
    assert len(res) >= 2


def test_command_injection_vulnerable(monkeypatch):
    called = {}

    def fake_popen(cmd, shell=False):
        called['cmd'] = cmd
        called['shell'] = shell
        class P: pass
        return P()

    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    ib.export_data("bad;echo INJ")
    assert called.get('shell') is True
    assert 'bad;echo INJ' in called.get('cmd')


def test_ssrf_vulnerable(monkeypatch):
    called = {}

    def fake_post(url, json=None):
        called['url'] = url
        called['json'] = json
        class R:
            text = 'ok'
        return R()

    monkeypatch.setattr(requests, 'post', fake_post)
    resp = ib.transfer_funds({"target": "t", "amount": 10, "notify_url": "http://example.com/notify"})
    assert called.get('url') == 'http://example.com/notify'


def test_update_records_vulnerable(tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text("a: 1\n")
    data = ib.update_records(str(outside))
    assert data.get('a') == 1

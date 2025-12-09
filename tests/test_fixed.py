import os
import sqlite3
import subprocess
import json
import tempfile
import zipfile
import requests
import importlib
import sys
import pathlib
# Ensure project root is importable when pytest runs from tests/ directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import input as im

DB = os.path.abspath("appdata.db")


def setup_module(module):
    # Set env keys used by input.py
    os.environ['API_KEY'] = 'testkey123'
    os.environ['PAYMENT_TOKEN'] = 'paytoken'
    os.environ['INTERNAL_AUTH'] = 'secret'

    # create a small database
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, name TEXT, balance REAL)")
    c.execute("DELETE FROM profiles")
    c.execute("INSERT INTO profiles (id,name,balance) VALUES (1, 'Alice', 1000)")
    conn.commit()
    conn.close()

    # create safe config dir
    safe_dir = os.path.abspath(os.path.join(os.getcwd(), 'configs'))
    os.makedirs(safe_dir, exist_ok=True)
    with open(os.path.join(safe_dir, 'ok.yaml'), 'w') as f:
        f.write('a: 1\n')


def test_sql_injection_fixed():
    res = im.query_profile("1' OR '1'='1")
    assert res == []
    res2 = im.query_profile('1')
    assert len(res2) == 1


def test_command_injection_fixed(monkeypatch, tmp_path):
    # ensure subprocess.Popen is not used
    def fake_popen(*args, **kwargs):
        raise AssertionError("subprocess.Popen should not be used")
    monkeypatch.setattr(subprocess, 'Popen', fake_popen)

    zip_path = im.export_data('safe_name')
    assert os.path.exists(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        assert 'appdata.db' in zf.namelist()


def test_ssrf_fixed(monkeypatch):
    called = {}
    def fake_post(url, json=None, headers=None, timeout=None):
        called['url'] = url
        class R:
            def raise_for_status(self):
                pass
            text = 'ok'
        return R()

    monkeypatch.setattr(requests, 'post', fake_post)
    # http should be rejected
    try:
        im.transfer_funds({"target": "t", "amount": 10, "notify_url": "http://example.com/notify"})
        assert False
    except ValueError:
        pass

    # https should be allowed and call post
    resp = im.transfer_funds({"target": "t", "amount": 10, "notify_url": "https://example.com/notify"})
    assert called.get('url') == 'https://example.com/notify'


def test_update_records_fixed():
    # valid
    cfg = im.update_records('ok.yaml')
    assert cfg.get('a') == 1

    # invalid - outside path
    try:
        im.update_records('../outside.yaml')
        assert False
    except ValueError:
        pass

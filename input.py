import os
import sqlite3
import hashlib
import hmac
import re
import json
import logging
from flask import Flask, request, jsonify, abort
import requests
import yaml
import zipfile
from io import BytesIO
from urllib.parse import urlparse

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Secrets and configuration must be provided via environment variables in production
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
INTERNAL_AUTH_KEY = os.environ.get("INTERNAL_AUTH_KEY")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
DB_FILE = os.environ.get("DB_FILE", "appdata.db")
ALLOWED_NOTIFY_HOSTS = os.environ.get("ALLOWED_NOTIFY_HOSTS", "localhost,127.0.0.1").split(",")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "configs")

# Simple environment checks
if not INTERNAL_AUTH_KEY or not ADMIN_API_KEY:
    logging.warning("INTERNAL_AUTH_KEY or ADMIN_API_KEY not set. Ensure environment variables are configured in production.")


def require_api_key(fn):
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or auth != f"Bearer {ADMIN_API_KEY}":
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def auth_user(info):
    username = info.get("username", "")
    if not username:
        return None
    # use HMAC-SHA256 with a server-side secret to generate tokens
    token = hmac.new(INTERNAL_AUTH_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
    return token


def query_profile(uid):
    # Enforce numeric user ids only and convert explicitly
    try:
        uid_str = str(int(uid))
    except Exception:
        raise ValueError("Invalid user id")
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT id,name,balance FROM profiles WHERE id = ?", (uid_str,))
        data = c.fetchall()
    finally:
        conn.close()
    return data


def is_allowed_notify_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https",):
            return False
        host = parsed.hostname
        if not host:
            return False
        # disallow private IP addresses and local addresses unless explicitly allowed
        if host not in ALLOWED_NOTIFY_HOSTS:
            return False
        return True
    except Exception:
        return False


def transfer_funds(payload):
    target = payload.get("target")
    amount = payload.get("amount")
    if not target or not amount:
        raise ValueError("target and amount are required")
    try:
        amount_value = float(amount)
    except Exception:
        raise ValueError("Invalid amount")
    url = payload.get("notify_url")
    if not url or not is_allowed_notify_url(url):
        raise ValueError("Invalid or disallowed notify_url")
    headers = {"Authorization": f"Bearer {PAYMENT_TOKEN}"} if PAYMENT_TOKEN else {}
    try:
        resp = requests.post(url, json={"amount": amount_value}, headers=headers, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to notify: %s", e)
        raise
    return resp.text


def update_records(path):
    # Only allow files under CONFIG_DIR
    if not path:
        raise ValueError("file path required")
    safe_path = os.path.normpath(os.path.join(CONFIG_DIR, os.path.basename(path)))
    if not safe_path.startswith(os.path.abspath(CONFIG_DIR)):
        raise ValueError("Invalid file path")
    if not os.path.exists(safe_path):
        raise FileNotFoundError("Config file not found")
    with open(safe_path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    # sanitize name
    if not name or not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
        raise ValueError("Invalid name")
    # create zip in memory and write database file
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_FILE, arcname=os.path.basename(DB_FILE))
    # write to disk
    out_path = f"{name}.zip"
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())
    return out_path


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json or {}
    token = auth_user(info)
    if not token:
        return jsonify({"error": "Invalid input"}), 400
    return jsonify({"token": token})


@app.route("/profile")
@require_api_key
def api_profile():
    uid = request.args.get("id")
    try:
        data = query_profile(uid)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/transfer", methods=["POST"])
@require_api_key
def api_transfer():
    p = request.json or {}
    try:
        return jsonify({"result": transfer_funds(p)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/config", methods=["POST"])
@require_api_key
def api_config():
    path = request.json.get("file")
    try:
        cfg = update_records(path)
        return jsonify(cfg)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/export")
@require_api_key
def api_export():
    name = request.args.get("name")
    try:
        out = export_data(name)
        return jsonify({"ok": 1, "file": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0")
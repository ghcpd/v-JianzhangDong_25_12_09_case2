import os
import sqlite3
import requests
import hmac
import hashlib
import logging
from flask import Flask, request, jsonify, abort
import yaml
import re
import zipfile
import tempfile
import ipaddress
from urllib.parse import urlparse

app = Flask(__name__)

# Load secrets from environment/config (do NOT hardcode)
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")
API_KEY = os.environ.get("API_KEY")

DB_FILE = os.path.abspath(os.environ.get("DB_FILE", "appdata.db"))
SAFE_CONFIG_DIR = os.path.abspath(os.environ.get("SAFE_CONFIG_DIR", os.path.join(os.getcwd(), "configs")))
MAX_TRANSFER_AMOUNT = float(os.environ.get("MAX_TRANSFER_AMOUNT", "10000"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def require_api_key(func):
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if not API_KEY or key != API_KEY:
            abort(401, description="Unauthorized")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def auth_user(info):
    username = info.get("username") if info else None
    if not username or not INTERNAL_AUTH:
        raise ValueError("Invalid authentication request")
    # Use HMAC-SHA256 with server secret to derive a token
    token = hmac.new(INTERNAL_AUTH.encode(), username.encode(), hashlib.sha256).hexdigest()
    return token


def query_profile(uid):
    try:
        uid_int = int(uid)
    except Exception:
        # Invalid id format -> do not query
        return []
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT id,name,balance FROM profiles WHERE id = ?", (uid_int,))
        data = c.fetchall()
        return data
    finally:
        conn.close()


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        host = parsed.hostname
        if not host:
            return False
        # Disallow private IPs
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private:
                return False
        except ValueError:
            # hostname is not an IP; ok
            pass
        return True
    except Exception:
        return False


def transfer_funds(payload):
    target = payload.get("target")
    amount = payload.get("amount")
    url = payload.get("notify_url")

    if not target or amount is None or url is None:
        raise ValueError("Missing transfer parameters")
    try:
        amount_val = float(amount)
    except Exception:
        raise ValueError("Invalid amount")
    if amount_val <= 0 or amount_val > MAX_TRANSFER_AMOUNT:
        raise ValueError("Amount out of allowed range")
    if not is_valid_url(url):
        raise ValueError("Invalid notify_url")

    logger.info("Initiating transfer to %s of amount %s", target, amount_val)
    headers = {"Content-Type": "application/json"}
    # Use PAYMENT_TOKEN from env; do not log token
    resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount_val}, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.text


def update_records(filename):
    # Allow only files within SAFE_CONFIG_DIR and with .yaml extension
    if not filename or not filename.endswith(".yaml"):
        raise ValueError("Invalid config filename; only .yaml allowed")
    full = os.path.abspath(os.path.join(SAFE_CONFIG_DIR, filename))
    if not full.startswith(SAFE_CONFIG_DIR + os.sep):
        raise ValueError("Access to the requested file is not allowed")
    if not os.path.exists(full):
        raise FileNotFoundError("Config file not found")
    with open(full) as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    # Sanitize name
    if not name or not re.match(r"^[A-Za-z0-9_-]+$", name):
        raise ValueError("Invalid export name")
    zip_path = os.path.abspath(f"{name}.zip")
    # Ensure DB_FILE exists
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError("Database file not found")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_FILE, os.path.basename(DB_FILE))
    return zip_path


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json
    try:
        token = auth_user(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"token": token})


@app.route("/profile")
@require_api_key
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
@require_api_key
def api_transfer():
    p = request.json
    try:
        result = transfer_funds(p)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"result": result})


@app.route("/config", methods=["POST"])
@require_api_key
def api_config():
    path = request.json.get("file")
    try:
        cfg = update_records(path)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(cfg)


@app.route("/export")
@require_api_key
def api_export():
    name = request.args.get("name")
    try:
        path = export_data(name)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": 1, "zip": path})


if __name__ == "__main__":
    # Do NOT run in debug mode by default
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)

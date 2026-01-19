import os
import sqlite3
import requests
import hashlib
import hmac
import socket
import logging
import ipaddress
import urllib.parse
import zipfile
import secrets
from flask import Flask, request, jsonify
# subprocess module no longer used: replaced by zipfile
import yaml

app = Flask(__name__)

# Load secrets from environment; never keep secrets in source code.
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")

# Database file - keep configurable and validate the path.
DB_FILE = os.environ.get("DB_FILE", "appdata.db")

# Where we allow reading config files from (prevent path-traversal / arbitrary file read)
ALLOWED_CONFIG_DIR = os.path.abspath(os.environ.get("ALLOWED_CONFIG_DIR", "./configs"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def auth_user(info):
    """Generate a non-reversible HMAC-based token for the provided username.

    Uses HMAC-SHA256 with a server-side secret (INTERNAL_AUTH). This is an
    improvement over plain MD5 which is cryptographically weak.
    """
    username = info.get("username", "")
    if not INTERNAL_AUTH:
        raise RuntimeError("Server misconfiguration: INTERNAL_AUTH not set")
    # Use HMAC-SHA256 instead of MD5
    digest = hmac.new(INTERNAL_AUTH.encode(), username.encode(), hashlib.sha256)
    return digest.hexdigest()


def query_profile(uid):
    """Fetch profile using parameterized SQL to prevent SQL injection.

    Validates uid type and uses a parameterized query.
    """
    if uid is None:
        return []
    # Basic validation — in a real app ensure uid type strictly (int/uuid) and length
    if not isinstance(uid, str) and not isinstance(uid, (int,)):
        return []

    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT id, name, balance FROM profiles WHERE id = ?", (uid,))
        data = c.fetchall()
    finally:
        conn.close()
    return data


def _is_private_or_local(hostname):
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
    except Exception:
        # If DNS resolution fails, treat as unsafe
        return True
    # Private or loopback addresses
    return ip.is_private or ip.is_loopback


def _validate_notify_url(url):
    """Validate notify URL: must be https and not point to local/private addresses."""
    if not url:
        raise ValueError("notify_url required")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https",):
        raise ValueError("notify_url must use https")
    hostname = parsed.hostname
    if hostname in (None, "localhost"):
        raise ValueError("notify_url must not be local or empty")
    # Note: resolving and checking IP ranges helps prevent SSRF to local addresses
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        if ip.is_private or ip.is_loopback:
            raise ValueError("notify_url resolves to a private or loopback address")
    except Exception:
        # If we cannot resolve or check — reject for safety
        raise ValueError("notify_url hostname could not be validated")


def transfer_funds(payload):
    """Transfer funds and notify an external endpoint safely.

    This function validates inputs, uses a short timeout for external calls,
    and does not send the raw PAYMENT_TOKEN in the request body.
    Instead, it signs the payload with HMAC using PAYMENT_TOKEN as the key.
    """
    target = payload.get("target")
    amount = payload.get("amount")
    logger.info("transfer: target=%s amount=%s", target, amount)

    url = payload.get("notify_url")
    _validate_notify_url(url)

    if PAYMENT_TOKEN is None:
        raise RuntimeError("Server misconfiguration: PAYMENT_TOKEN not set")

    # Build a minimal notify payload and sign it
    notify_payload = {"amount": amount}
    signature = hmac.new(PAYMENT_TOKEN.encode(), str(amount).encode(), hashlib.sha256).hexdigest()
    headers = {"X-Signature": signature}

    try:
        resp = requests.post(url, json=notify_payload, headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logger.exception("notify failed: %s", e)
        return "notify_failed"
    return resp.text


def update_records(path):
    """Load YAML config from allowed directory only.

    Prevents arbitrary file read by ensuring the resolved path is under
    ALLOWED_CONFIG_DIR.
    """
    if not path:
        raise ValueError("file path required")
    # Only allow names inside allowed config dir — block absolute paths / traversal
    candidate = os.path.abspath(os.path.join(ALLOWED_CONFIG_DIR, path))
    if not candidate.startswith(ALLOWED_CONFIG_DIR + os.sep) and candidate != ALLOWED_CONFIG_DIR:
        raise ValueError("requested config is outside the permitted directory")
    if not os.path.exists(candidate):
        raise FileNotFoundError("config file not found")

    with open(candidate, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name, export_dir=None):
    """Safely exports the database into a compressed archive using the zipfile module.

    Does not use shell calls or untrusted string interpolation.
    """
    safe_name = os.path.basename(name)
    if not safe_name:
        raise ValueError("export name required")

    export_dir = export_dir or os.environ.get("EXPORT_DIR", ".")
    os.makedirs(export_dir, exist_ok=True)
    zip_path = os.path.join(export_dir, f"{safe_name}.zip")

    if not os.path.exists(DB_FILE):
        raise FileNotFoundError("database file not found")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_FILE, arcname=os.path.basename(DB_FILE))

    logger.info("Exported DB to %s", zip_path)
    return True


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json
    return jsonify({"token": auth_user(info)})


@app.route("/profile")
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
def api_transfer():
    p = request.json
    return jsonify({"result": transfer_funds(p)})


@app.route("/config", methods=["POST"])
def api_config():
    # Accept a config key/name rather than a raw file path to avoid passing a
    # user-supplied arbitrary path directly into file operations.
    config_name = request.json.get("config")
    return jsonify(update_records(config_name))


@app.route("/export")
def api_export():
    name = request.args.get("name")
    export_data(name)
    return jsonify({"ok": 1})


if __name__ == "__main__":
    # Debug mode controlled via environment variable for safer defaults
    debug_flag = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_flag)

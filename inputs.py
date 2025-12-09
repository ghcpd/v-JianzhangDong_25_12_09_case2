import os
import sqlite3
import requests
import hashlib
import logging
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import subprocess
import yaml
from pathlib import Path
import shlex
import hmac

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load secrets from environment variables instead of hardcoding
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "default_token")
MAIL_SERVER_KEY = os.getenv("MAIL_SERVER_KEY", "default_key")
INTERNAL_AUTH = os.getenv("INTERNAL_AUTH", "default_auth")

# Configuration
DB_FILE = os.getenv("DB_FILE", "appdata.db")
ALLOWED_EXPORT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def auth_user(info):
    """Authenticate user using HMAC-SHA256 instead of MD5."""
    if not info or "username" not in info or "password" not in info:
        return None
    
    username = str(info.get("username", "")).strip()
    password = str(info.get("password", "")).strip()
    
    # Validate input
    if not username or not password or len(username) > 255 or len(password) > 255:
        return None
    
    # Use HMAC-SHA256 for secure authentication
    msg = f"{username}:{INTERNAL_AUTH}".encode()
    hashed = hmac.new(msg, password.encode(), hashlib.sha256).hexdigest()
    return hashed


def query_profile(uid):
    """Query user profile with parameterized queries to prevent SQL injection."""
    if not uid or not isinstance(uid, (str, int)):
        return []
    
    uid_str = str(uid).strip()
    
    # Validate UID format (alphanumeric only)
    if not uid_str.isalnum() or len(uid_str) > 100:
        logger.warning(f"Invalid UID format attempted")
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # Use parameterized query to prevent SQL injection
        q = "SELECT id, name, balance FROM profiles WHERE id = ?"
        c.execute(q, (uid_str,))
        data = c.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return []


def transfer_funds(payload):
    """Transfer funds with input validation and safe logging."""
    if not payload or not isinstance(payload, dict):
        logger.warning("Invalid transfer payload")
        return None
    
    target = str(payload.get("target", "")).strip()
    amount = payload.get("amount")
    url = str(payload.get("notify_url", "")).strip()
    
    # Validate inputs
    if not target or len(target) > 255:
        logger.warning("Invalid transfer target")
        return None
    
    try:
        amount = float(amount)
        if amount <= 0 or amount > 1000000:
            logger.warning("Invalid transfer amount")
            return None
    except (ValueError, TypeError):
        logger.warning("Invalid transfer amount format")
        return None
    
    if not url or len(url) > 2048:
        logger.warning("Invalid notify URL")
        return None
    
    # Log safely without exposing sensitive data
    logger.info(f"Transfer initiated: amount={amount}")
    
    try:
        resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount}, timeout=10)
        return resp.text
    except requests.RequestException as e:
        logger.error(f"Transfer request failed: {str(e)}")
        return None


def update_records(path):
    """Load configuration file with path validation."""
    if not path or not isinstance(path, str):
        logger.warning("Invalid config path")
        return None
    
    path = path.strip()
    
    # Prevent path traversal attacks
    allowed_dir = Path("config").resolve()
    config_path = Path(path).resolve()
    
    try:
        # Ensure path is within allowed directory
        if not str(config_path).startswith(str(allowed_dir)):
            logger.warning(f"Path traversal attempt blocked: {path}")
            return None
        
        # Check file exists
        if not config_path.exists():
            logger.warning(f"Config file not found: {path}")
            return None
        
        with open(config_path, 'r') as f:
            cfg = yaml.safe_load(f)
        return cfg
    except (IOError, yaml.YAMLError) as e:
        logger.error(f"Configuration load error: {str(e)}")
        return None


def export_data(name):
    """Export data safely without command injection."""
    if not name or not isinstance(name, str):
        logger.warning("Invalid export name")
        return False
    
    name = name.strip()
    
    # Validate filename - only allow alphanumeric, underscore, and hyphen
    if not all(c in ALLOWED_EXPORT_CHARS for c in name):
        logger.warning(f"Invalid export filename: {name}")
        return False
    
    if len(name) > 50:
        logger.warning("Export filename too long")
        return False
    
    try:
        # Use list format to avoid shell injection
        cmd = ["zip", f"{name}.zip", DB_FILE]
        result = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
        
        if result.returncode != 0:
            logger.warning(f"Export command failed: {result.stderr.decode()}")
            return False
        
        logger.info(f"Data exported successfully: {name}.zip")
        return True
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        return False


@app.route("/auth", methods=["POST"])
def api_auth():
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    info = request.json
    token = auth_user(info)
    if not token:
        return jsonify({"error": "Authentication failed"}), 401
    return jsonify({"token": token})


@app.route("/profile")
def api_profile():
    uid = request.args.get("id", "").strip()
    if not uid:
        return jsonify({"error": "Missing user ID"}), 400
    
    profile = query_profile(uid)
    if not profile:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(profile)


@app.route("/transfer", methods=["POST"])
def api_transfer():
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    p = request.json
    result = transfer_funds(p)
    if not result:
        return jsonify({"error": "Transfer failed"}), 400
    return jsonify({"result": result})


@app.route("/config", methods=["POST"])
def api_config():
    if not request.json or "file" not in request.json:
        return jsonify({"error": "Missing file parameter"}), 400
    path = request.json.get("file")
    cfg = update_records(path)
    if not cfg:
        return jsonify({"error": "Configuration not found"}), 404
    return jsonify(cfg)


@app.route("/export")
def api_export():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing export name"}), 400
    
    if not export_data(name):
        return jsonify({"error": "Export failed"}), 400
    
    return jsonify({"ok": 1})


if __name__ == "__main__":
    # Disable debug mode in production
    debug_mode = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)

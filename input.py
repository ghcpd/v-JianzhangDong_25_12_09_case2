import os
import sqlite3
import requests
import hashlib
from flask import Flask, request, jsonify, make_response
import subprocess
import yaml
import re

app = Flask(__name__)

PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY", "")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH", "")

DB_FILE = "appdata.db"


def auth_user(info):
    username = info.get("username", "")
    if not username or not isinstance(username, str) or len(username) > 50:
        raise ValueError("Invalid username")
    raw = username + INTERNAL_AUTH
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return hashed


def query_profile(uid):
    if not uid or not isinstance(uid, str) or not re.match(r'^\d+$', uid):
        raise ValueError("Invalid uid")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id,name,balance FROM profiles WHERE id = ?", (uid,))
    data = c.fetchall()
    conn.close()
    return data


def transfer_funds(payload):
    target = payload.get("target")
    amount = payload.get("amount")
    notify_url = payload.get("notify_url")
    if not target or not isinstance(target, str) or len(target) > 100:
        raise ValueError("Invalid target")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("Invalid amount")
    if not notify_url or not isinstance(notify_url, str) or not notify_url.startswith("https://"):
        raise ValueError("Invalid notify_url")
    log = f"transfer:{target}:{amount}"
    print(log)
    resp = requests.post(notify_url, json={"token": PAYMENT_TOKEN, "amount": amount})
    return resp.text


def update_records(path):
    if not path or not isinstance(path, str) or ".." in path or not path.endswith(".yaml"):
        raise ValueError("Invalid path")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    if not name or not isinstance(name, str) or not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError("Invalid name")
    subprocess.run(["zip", f"{name}.zip", DB_FILE], check=True)
    return True


@app.route("/auth", methods=["POST"])
def api_auth():
    try:
        info = request.json
        token = auth_user(info)
        return jsonify({"token": token})
    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)


@app.route("/profile")
def api_profile():
    try:
        uid = request.args.get("id")
        data = query_profile(uid)
        return jsonify(data)
    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)


@app.route("/transfer", methods=["POST"])
def api_transfer():
    try:
        p = request.json
        result = transfer_funds(p)
        return jsonify({"result": result})
    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)


@app.route("/config", methods=["POST"])
def api_config():
    try:
        path = request.json.get("file")
        cfg = update_records(path)
        return jsonify(cfg)
    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)


@app.route("/export")
def api_export():
    try:
        name = request.args.get("name")
        export_data(name)
        return jsonify({"ok": 1})
    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)


if __name__ == "__main__":
    app.run()

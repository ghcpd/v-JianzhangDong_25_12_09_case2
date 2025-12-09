import sqlite3
import subprocess
import time
import requests
import os
import sys
import signal

import socket


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def prepare_db(db_path='appdata.db'):
    # Don't delete DB if it's locked by a server; instead reset contents safely
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS profiles')
    c.execute('CREATE TABLE profiles (id TEXT PRIMARY KEY, name TEXT, balance REAL)')
    c.execute("INSERT OR REPLACE INTO profiles (id,name,balance) VALUES ('1','Alice',100.0)")
    c.execute("INSERT OR REPLACE INTO profiles (id,name,balance) VALUES ('2','Bob',200.0)")
    conn.commit()
    conn.close()


def start_server(target_file):
    # pick a free port and run the Flask app via `flask run --no-reload` to avoid werkzeug reloader issues
    port = find_free_port()
    env = os.environ.copy()
    env['PAYMENT_TOKEN'] = 'test_payment_token'
    env['INTERNAL_AUTH_KEY'] = 'test_internal_key'
    env['ADMIN_API_KEY'] = 'test_admin_api'
    env['FLASK_DEBUG'] = '0'
    env['FLASK_APP'] = target_file
    env['FLASK_RUN_PORT'] = str(port)
    env['FLASK_RUN_HOST'] = '127.0.0.1'
    env['PYTHONUNBUFFERED'] = '1'
    # ensure config dir exists for fixed server
    os.makedirs('configs', exist_ok=True)
    with open('configs/sample.yml', 'w') as f:
        f.write('sample: true')
    # run `flask run --no-reload --port {port}`
    cmd = ['flask', 'run', '--no-reload', '--port', str(port), '--host', '127.0.0.1']
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base = f'http://127.0.0.1:{port}'
    # expose global BASE for tests
    globals()['BASE'] = base
    return proc, base


def wait_for_server(timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f'{BASE}/')
            return True
        except Exception:
            time.sleep(0.2)
    return False


def test_sql_injection(expected_vulnerable=True):
    # craft injection that uses SQL comment to neutralize the trailing quote
    injection = "1' OR '1'='1' -- "
    params = {'id': injection}
    headers = {'Authorization': 'Bearer test_admin_api'}
    try:
        r = requests.get(f"{BASE}/profile", params=params, headers=headers, timeout=5)
        data = r.json()
    except Exception as e:
        print('SQLi request failed or invalid JSON:', e)
        return False
    if expected_vulnerable:
        if isinstance(data, list) and len(data) > 1:
            print('SQL injection succeeded (vulnerable)')
            return True
        else:
            print('SQL injection not observed (unexpected)')
            return False
    else:
        # secure if server returns error or a single/zero record
        if isinstance(data, dict) and ('error' in data or 'Invalid' in str(data)):
            print('SQL injection prevented with error response (secure)')
            return True
        if isinstance(data, list) and len(data) <= 1:
            print('SQL injection prevented (secure)')
            return True
        print('SQL injection still possible (vulnerable)')
        return False


def test_path_traversal(expected_vulnerable=True):
    # create a sensitive file outside of config dir
    outside_dir = os.path.abspath('.')
    outside_file = os.path.join(outside_dir, 'sensitive_it.txt')
    with open(outside_file, 'w') as f:
        f.write('SENSITIVE_CONTENT')
    # use an absolute path to test traversal; fixed apps should reject absolute paths
    payload = {'file': outside_file}
    headers = {'Authorization': 'Bearer test_admin_api'}
    try:
        r = requests.post(f"{BASE}/config", json=payload, headers=headers, timeout=5)
    except Exception as e:
        print('Path traversal request failed:', e)
        return False
    if expected_vulnerable:
        # vulnerable versions will return the file content / parsed YAML
        if r.status_code == 200 and 'SENSITIVE_CONTENT' in r.text:
            print('Path traversal succeeded (vulnerable)')
            os.remove(outside_file)
            return True
        else:
            print('Path traversal not observed (unexpected)')
            os.remove(outside_file)
            return False
    else:
        # secure app should reject paths outside config dir
        if r.status_code != 200:
            print('Path traversal prevented (secure)')
            os.remove(outside_file)
            return True
        else:
            print('Path traversal still possible (vulnerable)')
            os.remove(outside_file)
            return False


def _start_callback_server(listen_port=9999, wait_for=2):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    received = {'called': False, 'body': None}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            received['called'] = True
            received['body'] = body
            self.send_response(200)
            self.end_headers()
        def log_message(self, format, *args):
            return

    server = HTTPServer(('127.0.0.1', listen_port), Handler)

    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)
    return server, received


def test_ssrf(expected_vulnerable=True):
    server, received = _start_callback_server()
    payload = {'target': '1', 'amount': '12.3', 'notify_url': 'http://127.0.0.1:9999/notify'}
    headers = {'Authorization': 'Bearer test_admin_api'}
    try:
        r = requests.post(f"{BASE}/transfer", json=payload, headers=headers, timeout=5)
    except Exception as e:
        print('SSRF request failed:', e)
        server.shutdown()
        return False
    # give server a moment
    time.sleep(0.5)
    called = received['called']
    body = received['body']
    server.shutdown()
    if expected_vulnerable:
        if called and body and 'token' in body:
            print('SSRF/callback received and token present (vulnerable)')
            return True
        else:
            print('SSRF not observed (unexpected)')
            return False
    else:
        if not called:
            print('No callback (secure)')
            return True
        else:
            print('Callback received (vulnerable)')
            return False


def test_export_unsafe_name(expected_vulnerable=True):
    # use a name with unsafe chars
    name = "bad;touch_me"
    headers = {'Authorization': 'Bearer test_admin_api'}
    try:
        r = requests.get(f"{BASE}/export", params={'name': name}, headers=headers, timeout=5)
    except Exception as e:
        print('Export request failed:', e)
        return False
    if expected_vulnerable:
        # vulnerable app returns 200 and possibly created a file
        if r.status_code == 200:
            print('Export accepted unsafe name (vulnerable)')
            return True
        else:
            print('Export did not accept unsafe name (unexpected)')
            return False
    else:
        if r.status_code != 200:
            print('Unsafe name rejected (secure)')
            return True
        else:
            print('Unsafe name accepted (vulnerable)')
            return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: test_runner.py <target_file>')
        sys.exit(2)
    target = sys.argv[1]
    prepare_db()
    proc, base = start_server(target)
    try:
        # wait for server to be ready
        for i in range(40):
            try:
                requests.get(f'{base}/', timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        expected_vulnerable = True if 'backup' in target else False
        results = []
        results.append(('SQLi', test_sql_injection(expected_vulnerable)))
        results.append(('PathTraversal', test_path_traversal(expected_vulnerable)))
        results.append(('SSRF', test_ssrf(expected_vulnerable)))
        results.append(('ExportName', test_export_unsafe_name(expected_vulnerable)))

        vulnerable_found = any([not r[1] for r in results]) if not expected_vulnerable else any([r[1] for r in results])
        # Print detailed results
        for name, ok in results:
            print(f'{name}:', 'VULNERABLE' if ok and expected_vulnerable else ('SECURE' if ok and not expected_vulnerable else ('FAILED' if not ok else 'UNKNOWN')))

        # For backup target we expect vulnerabilities to be found; for fixed target we expect NONE
        final_ok = True
        if expected_vulnerable:
            if vulnerable_found:
                final_ok = True
            else:
                final_ok = False
        else:
            if vulnerable_found:
                final_ok = False
            else:
                final_ok = True

        print('TEST RESULT for', target, '->', 'PASS' if final_ok else 'FAIL')
        sys.exit(0 if final_ok else 1)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: test_runner.py <target_file>')
        sys.exit(2)
    target = sys.argv[1]
    prepare_db()
    proc = start_server(target)
    try:
        # wait for server to be ready
        time.sleep(1)
        # try a few times to connect
        for i in range(20):
            try:
                requests.get(f'{BASE}/', timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        # decide expected behavior
        expected_vulnerable = True if 'backup' in target else False
        ok = test_sql_injection(expected_vulnerable=expected_vulnerable)
        print('TEST RESULT for', target, '->', 'PASS' if ok else 'FAIL')
        sys.exit(0 if ok else 1)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
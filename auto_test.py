import os
import platform
import subprocess
import datetime

LOG_DIR = os.path.join('logs')
LOG_FILE = os.path.join(LOG_DIR, 'test_run.log')
os.makedirs(LOG_DIR, exist_ok=True)


def _log(msg):
    ts = datetime.datetime.utcnow().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")


def run_script(cmd, cwd=None):
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = []
    for line in proc.stdout:
        _log(line.rstrip())
        out.append(line)
    proc.wait()
    return proc.returncode, ''.join(out)


if __name__ == '__main__':
    _log('Starting automated tests')
    system = platform.system()
    if system == 'Windows':
        runner = 'run_test.bat'
    else:
        runner = './run_test.sh'

    overall_ok = True
    # Run backup then fixed explicitly
    for target in ['backup', 'fixed']:
        _log(f'Running tests for target: {target}')
        if system == 'Windows':
            cmd = f"{runner} {target}"
        else:
            cmd = f"{runner} {target}"
        rc, output = run_script(cmd)
        if rc == 0:
            _log(f'{target} TEST PASSED')
        else:
            _log(f'{target} TEST FAILED')
            overall_ok = False
    _log('TEST PASSED' if overall_ok else 'TEST FAILED')
    exit(0 if overall_ok else 1)

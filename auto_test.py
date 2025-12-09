import os
import platform
import subprocess
import sys
from datetime import datetime

LOG_DIR = os.path.join("logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "test_run.log")

TARGETS = ["inputs_backup.py", "inputs.py"]


def now_ts():
    return datetime.utcnow().isoformat() + "Z"


def detect_env():
    plat = platform.system().lower()
    # simple docker detection
    is_docker = False
    try:
        if os.path.exists('/.dockerenv'):
            is_docker = True
        else:
            with open('/proc/1/cgroup', 'r') as fh:
                if 'docker' in fh.read():
                    is_docker = True
    except Exception:
        pass
    return plat, is_docker


def run_test_for_file(file_path):
    plat, is_docker = detect_env()
    if plat.startswith('windows'):
        runner = ['run_test.bat', file_path]
        shell = True
    else:
        # use run_test.sh
        runner = ['bash', 'run_test.sh', file_path]
        shell = False

    start = now_ts()
    proc = subprocess.Popen(runner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell, universal_newlines=True)
    out, _ = proc.communicate()
    end = now_ts()
    status = 'TEST PASSED' if proc.returncode == 0 else 'TEST FAILED'
    return {
        'file': file_path,
        'start': start,
        'end': end,
        'returncode': proc.returncode,
        'output': out,
        'status': status
    }


if __name__ == '__main__':
    overall_ok = True
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f"=== RUN at {now_ts()} ===\n")
        for t in TARGETS:
            log.write(f"-- Testing {t} --\n")
            print(f"Running tests for {t}")
            res = run_test_for_file(t)
            log.write(f"Start: {res['start']}\n")
            log.write(res['output'] + "\n")
            log.write(f"End: {res['end']}\nResult: {res['status']}\n")
            print(res['output'])
            if res['returncode'] != 0:
                overall_ok = False
        final_status = 'TEST PASSED' if overall_ok else 'TEST FAILED'
        log.write(f"=== FINAL STATUS: {final_status} at {now_ts()} ===\n\n")
    print(final_status)
    sys.exit(0 if overall_ok else 1)

import os
import platform
import subprocess
import datetime

LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'test_run.log')

os.makedirs(LOG_DIR, exist_ok=True)


def timestamp():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')


def run_script(script, shell=False):
    start = datetime.datetime.utcnow()
    try:
        if shell:
            proc = subprocess.run(script, shell=True, capture_output=True, text=True)
        else:
            proc = subprocess.run(script, capture_output=True, text=True)
    except Exception as e:
        return (1, str(e))
    duration = datetime.datetime.utcnow() - start
    out = proc.stdout + '\n' + proc.stderr
    return (proc.returncode, out)


if __name__ == '__main__':
    log('--- TEST RUN START: ' + timestamp())

    # Run per-file tests and log outputs directly to avoid platform script hangs
    overall_ok = True
    for target in ['input_backup.py', 'input.py']:
        log('---')
        log('TEST TARGET: ' + target)
        code, out = run_script(['python', 'tests/test_runner.py', target])
        log('TIMESTAMP: ' + timestamp())
        log('OUTPUT:')
        log(out)
        status = 'TEST PASSED' if code == 0 else 'TEST FAILED'
        log('STATUS: ' + status)
        if code != 0:
            overall_ok = False

    final_status = 'TEST PASSED' if overall_ok else 'TEST FAILED'
    log('---')
    log('FINAL STATUS: ' + final_status)
    log('--- TEST RUN END: ' + timestamp())

    print(final_status)
    exit(0 if overall_ok else 1)
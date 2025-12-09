import platform
import subprocess
import time
import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "test_run.log")

os.makedirs(LOG_DIR, exist_ok=True)

PYTHON_EXE = "D:/vscoderprojects/v-JianzhangDong_25_12_09_case2/grok-fast/v-JianzhangDong_25_12_09_case2/.venv/Scripts/python.exe"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def run_test_for_file(file_name):
    log_message(f"Starting test for {file_name}")
    
    # Start Flask app in background
    process = subprocess.Popen([PYTHON_EXE, file_name], stdout=None, stderr=None)
    time.sleep(5)  # Wait for app to start
    
    # Determine test script
    system = platform.system()
    if system == "Windows":
        test_script = "run_test.bat"
    else:
        test_script = "./run_test.sh"
    
    # Run test script
    result = subprocess.run([test_script], capture_output=True, text=True)
    
    # Log output
    log_message(f"Test output for {file_name}: {result.stdout}")
    if result.stderr:
        log_message(f"Test errors for {file_name}: {result.stderr}")
    
    # Kill Flask process
    process.terminate()
    process.wait()
    
    status = "TEST PASSED" if result.returncode == 0 else "TEST FAILED"
    log_message(f"{file_name}: {status}")
    return result.returncode == 0

def main():
    log_message("Starting automatic test execution")
    
    files = ["input_backup.py", "input.py"]
    all_passed = True
    
    for file in files:
        passed = run_test_for_file(file)
        if not passed:
            all_passed = False
    
    final_status = "TEST PASSED" if all_passed else "TEST FAILED"
    log_message(f"Overall: {final_status}")

if __name__ == "__main__":
    main()
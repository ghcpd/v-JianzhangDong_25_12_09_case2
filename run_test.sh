#!/bin/bash

# run_test.sh - Test script for Linux/macOS
# This script tests both the vulnerable backup and the secured version

set -e

test_file="${1:-inputs.py}"
LOGFILE="logs/test_run.log"

# Create logs directory if it doesn't exist
mkdir -p logs

# Timestamp function
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Run basic Python syntax check
test_syntax() {
    local file=$1
    echo "[$(get_timestamp)] Testing syntax for: $file" | tee -a "$LOGFILE"
    
    if python3 -m py_compile "$file" 2>&1 | tee -a "$LOGFILE"; then
        echo "[$(get_timestamp)] ✓ Syntax check passed for $file" | tee -a "$LOGFILE"
        return 0
    else
        echo "[$(get_timestamp)] ✗ Syntax check failed for $file" | tee -a "$LOGFILE"
        return 1
    fi
}

# Run security checks
test_security() {
    local file=$1
    echo "[$(get_timestamp)] Running security checks for: $file" | tee -a "$LOGFILE"
    
    local failed=0
    
    # Check for hardcoded secrets (should only be in backup)
    if grep -q "tok_production_998877\|mail_srv_key_ABCDEFG" "$file" 2>/dev/null; then
        echo "[$(get_timestamp)] WARNING: Hardcoded secrets detected in $file" | tee -a "$LOGFILE"
        if [[ "$file" == "inputs_backup.py" ]]; then
            echo "[$(get_timestamp)] ✓ Expected for backup file" | tee -a "$LOGFILE"
        else
            echo "[$(get_timestamp)] ✗ Security issue: Secrets in production file" | tee -a "$LOGFILE"
            failed=1
        fi
    fi
    
    # Check for SQL injection vulnerability (should only be in backup)
    if grep -q "WHERE id = '%s'" "$file" 2>/dev/null; then
        echo "[$(get_timestamp)] WARNING: SQL injection pattern detected in $file" | tee -a "$LOGFILE"
        if [[ "$file" == "inputs_backup.py" ]]; then
            echo "[$(get_timestamp)] ✓ Expected for backup file" | tee -a "$LOGFILE"
        else
            echo "[$(get_timestamp)] ✗ Security issue: SQL injection in production file" | tee -a "$LOGFILE"
            failed=1
        fi
    fi
    
    # Check for shell=True vulnerability (should only be in backup)
    if grep -q "shell=True" "$file" 2>/dev/null; then
        echo "[$(get_timestamp)] WARNING: shell=True detected in $file" | tee -a "$LOGFILE"
        if [[ "$file" == "inputs_backup.py" ]]; then
            echo "[$(get_timestamp)] ✓ Expected for backup file" | tee -a "$LOGFILE"
        else
            echo "[$(get_timestamp)] ✗ Security issue: Command injection in production file" | tee -a "$LOGFILE"
            failed=1
        fi
    fi
    
    # Check for MD5 usage in non-backup files
    if [[ "$file" != "inputs_backup.py" ]]; then
        if grep -q "hashlib.md5" "$file" 2>/dev/null; then
            echo "[$(get_timestamp)] ✗ Security issue: Weak MD5 hash in $file" | tee -a "$LOGFILE"
            failed=1
        else
            echo "[$(get_timestamp)] ✓ No weak MD5 hashing detected" | tee -a "$LOGFILE"
        fi
    fi
    
    # Check for proper environment variable usage in production file
    if [[ "$file" == "inputs.py" ]]; then
        if grep -q 'os.getenv' "$file" 2>/dev/null; then
            echo "[$(get_timestamp)] ✓ Environment variable usage detected" | tee -a "$LOGFILE"
        else
            echo "[$(get_timestamp)] ✗ Missing environment variable usage" | tee -a "$LOGFILE"
            failed=1
        fi
    fi
    
    # Check for parameterized queries in production file
    if [[ "$file" == "inputs.py" ]]; then
        if grep -q 'c.execute(q, (' "$file" 2>/dev/null; then
            echo "[$(get_timestamp)] ✓ Parameterized queries detected" | tee -a "$LOGFILE"
        else
            echo "[$(get_timestamp)] ✗ Missing parameterized queries" | tee -a "$LOGFILE"
            failed=1
        fi
    fi
    
    return $failed
}

# Test imports
test_imports() {
    local file=$1
    echo "[$(get_timestamp)] Testing imports for: $file" | tee -a "$LOGFILE"
    
    if python3 -c "import ast; ast.parse(open('$file').read())" 2>&1 | tee -a "$LOGFILE"; then
        echo "[$(get_timestamp)] ✓ Import test passed for $file" | tee -a "$LOGFILE"
        return 0
    else
        echo "[$(get_timestamp)] ✗ Import test failed for $file" | tee -a "$LOGFILE"
        return 1
    fi
}

# Main test execution
main() {
    echo "====================================" | tee -a "$LOGFILE"
    echo "Test Execution Started" | tee -a "$LOGFILE"
    echo "Timestamp: $(get_timestamp)" | tee -a "$LOGFILE"
    echo "====================================" | tee -a "$LOGFILE"
    echo "" | tee -a "$LOGFILE"
    
    local all_passed=0
    
    # Test backup file
    echo "Testing inputs_backup.py (Vulnerable Version)" | tee -a "$LOGFILE"
    echo "---" | tee -a "$LOGFILE"
    if test_syntax "inputs_backup.py"; then
        test_security "inputs_backup.py"
        test_imports "inputs_backup.py"
    else
        all_passed=1
    fi
    echo "" | tee -a "$LOGFILE"
    
    # Test production file
    echo "Testing inputs.py (Secured Version)" | tee -a "$LOGFILE"
    echo "---" | tee -a "$LOGFILE"
    if test_syntax "inputs.py"; then
        if test_security "inputs.py"; then
            test_imports "inputs.py"
        else
            all_passed=1
        fi
    else
        all_passed=1
    fi
    echo "" | tee -a "$LOGFILE"
    
    # Summary
    echo "====================================" | tee -a "$LOGFILE"
    echo "Test Execution Completed" | tee -a "$LOGFILE"
    echo "Timestamp: $(get_timestamp)" | tee -a "$LOGFILE"
    if [ $all_passed -eq 0 ]; then
        echo "Status: TEST PASSED" | tee -a "$LOGFILE"
        echo "====================================" | tee -a "$LOGFILE"
        return 0
    else
        echo "Status: TEST FAILED" | tee -a "$LOGFILE"
        echo "====================================" | tee -a "$LOGFILE"
        return 1
    fi
}

# Run tests
main
exit $?

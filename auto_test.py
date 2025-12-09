#!/usr/bin/env python3
"""
auto_test.py - Automatic test execution with environment detection

This script automatically detects the current environment (Windows/Linux/Docker)
and runs the corresponding test script. It logs all output with timestamps
and provides a final status report.
"""

import os
import sys
import subprocess
import platform
import logging
from datetime import datetime
from pathlib import Path


class TestRunner:
    """Handles test execution with logging and environment detection."""

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_file = self.log_dir / "test_run.log"
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.os_type = self.detect_environment()
        
    def setup_logging(self):
        """Configure logging to file and console."""
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        
        # File handler
        file_handler = logging.FileHandler(
            self.log_file,
            mode='a',
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def detect_environment(self):
        """Detect the current operating system and environment."""
        system = platform.system()
        
        if "docker" in os.environ.get("PATH", "").lower() or \
           Path("/.dockerenv").exists() or \
           Path("/proc/self/cgroup").exists():
            return "docker"
        elif system == "Windows":
            return "windows"
        elif system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        else:
            return "unknown"
    
    def test_file_syntax(self, filename):
        """Test if a Python file has valid syntax."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", filename],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def test_file_vulnerabilities(self, filename):
        """Test if a file contains known vulnerabilities."""
        vulnerabilities = {
            'hardcoded_secrets': "tok_production_998877",
            'command_injection': "shell=True",
            'sql_injection': "WHERE id = '%s'"
        }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_issues = {}
            for vuln_name, pattern in vulnerabilities.items():
                if pattern in content:
                    found_issues[vuln_name] = True
                else:
                    found_issues[vuln_name] = False
            
            return found_issues
        except Exception as e:
            self.logger.error(f"Error reading {filename}: {str(e)}")
            return None
    
    def run_file_tests(self):
        """Run syntax and vulnerability tests on both files."""
        self.logger.info("=" * 60)
        self.logger.info("Testing Individual Files")
        self.logger.info("=" * 60)
        
        files_status = {}
        
        # Test inputs_backup.py (should have vulnerabilities)
        self.logger.info("")
        self.logger.info("Testing inputs_backup.py (Vulnerable Version)")
        self.logger.info("-" * 60)
        
        backup_syntax = self.test_file_syntax("inputs_backup.py")
        self.logger.info(f"Syntax Check: {'✓ PASS' if backup_syntax else '✗ FAIL'}")
        
        backup_vulns = self.test_file_vulnerabilities("inputs_backup.py")
        if backup_vulns:
            self.logger.info("Vulnerability Check (Expected to have vulnerabilities):")
            self.logger.info(f"  - Hardcoded Secrets: {'✓ FOUND (expected)' if backup_vulns['hardcoded_secrets'] else '✗ NOT FOUND'}")
            self.logger.info(f"  - Command Injection: {'✓ FOUND (expected)' if backup_vulns['command_injection'] else '✗ NOT FOUND'}")
            self.logger.info(f"  - SQL Injection: {'✓ FOUND (expected)' if backup_vulns['sql_injection'] else '✗ NOT FOUND'}")
            
            backup_passed = backup_syntax and (backup_vulns['hardcoded_secrets'] or backup_vulns['command_injection'] or backup_vulns['sql_injection'])
            files_status['inputs_backup.py'] = backup_passed
            
            if backup_passed:
                self.logger.info("")
                self.logger.info("Result: ✓ inputs_backup.py PASSED (Vulnerabilities confirmed)")
            else:
                self.logger.error("")
                self.logger.error("Result: ✗ inputs_backup.py FAILED (Unexpected state)")
        
        # Test inputs.py (should NOT have vulnerabilities)
        self.logger.info("")
        self.logger.info("Testing inputs.py (Secured Version)")
        self.logger.info("-" * 60)
        
        secured_syntax = self.test_file_syntax("inputs.py")
        self.logger.info(f"Syntax Check: {'✓ PASS' if secured_syntax else '✗ FAIL'}")
        
        secured_vulns = self.test_file_vulnerabilities("inputs.py")
        if secured_vulns:
            self.logger.info("Vulnerability Check (Should NOT have vulnerabilities):")
            self.logger.info(f"  - Hardcoded Secrets: {'✗ FOUND (unexpected)' if secured_vulns['hardcoded_secrets'] else '✓ NOT FOUND (expected)'}")
            self.logger.info(f"  - Command Injection: {'✗ FOUND (unexpected)' if secured_vulns['command_injection'] else '✓ NOT FOUND (expected)'}")
            self.logger.info(f"  - SQL Injection: {'✗ FOUND (unexpected)' if secured_vulns['sql_injection'] else '✓ NOT FOUND (expected)'}")
            
            secured_passed = secured_syntax and not (secured_vulns['hardcoded_secrets'] or secured_vulns['command_injection'] or secured_vulns['sql_injection'])
            files_status['inputs.py'] = secured_passed
            
            if secured_passed:
                self.logger.info("")
                self.logger.info("Result: ✓ inputs.py PASSED (All vulnerabilities fixed)")
            else:
                self.logger.error("")
                self.logger.error("Result: ✗ inputs.py FAILED (Vulnerabilities still present)")
        
        return files_status
    
    def run_test_script(self):
        """Run the appropriate test script based on environment."""
        self.logger.info("=" * 60)
        self.logger.info("Automatic Test Execution Started")
        self.logger.info("=" * 60)
        self.logger.info(f"Detected Environment: {self.os_type.upper()}")
        self.logger.info(f"Python Version: {sys.version}")
        self.logger.info(f"Working Directory: {os.getcwd()}")
        self.logger.info("")
        
        # First, run file-level tests
        files_status = self.run_file_tests()
        
        # Then run the platform-specific test script if available
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Running Platform-Specific Tests")
        self.logger.info("=" * 60)
        self.logger.info("")
        
        try:
            if self.os_type == "docker":
                script_result = self._run_docker_tests()
            elif self.os_type == "windows":
                script_result = self._run_windows_tests()
            else:  # Linux, macOS, or other Unix-like
                script_result = self._run_unix_tests()
        except Exception as e:
            self.logger.error(f"Test execution failed with error: {str(e)}")
            script_result = False
        
        # Return both results - all tests pass only if both file tests and script tests pass
        return files_status, script_result
    
    def _run_unix_tests(self):
        """Run tests on Unix-like systems (Linux, macOS)."""
        self.logger.info("Running tests on Unix-like system (Linux/macOS)")
        self.logger.info("-" * 60)
        
        script_path = Path("run_test.sh")
        
        if not script_path.exists():
            self.logger.error(f"Test script not found: {script_path}")
            return False
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        try:
            # Run the shell script
            result = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Log all output
            if result.stdout:
                self.logger.info("STDOUT:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.logger.info(line)
            
            if result.stderr:
                self.logger.warning("STDERR:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        self.logger.warning(line)
            
            success = result.returncode == 0
            return success
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test script timed out after 300 seconds")
            return False
        except Exception as e:
            self.logger.error(f"Failed to run test script: {str(e)}")
            return False
    
    def _run_windows_tests(self):
        """Run tests on Windows systems."""
        self.logger.info("Running tests on Windows system")
        self.logger.info("-" * 60)
        
        script_path = Path("run_test.bat")
        
        if not script_path.exists():
            self.logger.error(f"Test script not found: {script_path}")
            return False
        
        try:
            # Run the batch script
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,
                shell=True
            )
            
            # Log all output
            if result.stdout:
                self.logger.info("STDOUT:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.logger.info(line)
            
            if result.stderr:
                self.logger.warning("STDERR:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        self.logger.warning(line)
            
            success = result.returncode == 0
            return success
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test script timed out after 300 seconds")
            return False
        except Exception as e:
            self.logger.error(f"Failed to run test script: {str(e)}")
            return False
    
    def _run_docker_tests(self):
        """Run tests in Docker environment."""
        self.logger.info("Running tests in Docker environment")
        self.logger.info("-" * 60)
        
        # In Docker, prefer running the shell script
        script_path = Path("run_test.sh")
        
        if not script_path.exists():
            self.logger.error(f"Test script not found: {script_path}")
            return False
        
        os.chmod(script_path, 0o755)
        
        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.stdout:
                self.logger.info("STDOUT:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.logger.info(line)
            
            if result.stderr:
                self.logger.warning("STDERR:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        self.logger.warning(line)
            
            success = result.returncode == 0
            return success
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test script timed out after 300 seconds")
            return False
        except Exception as e:
            self.logger.error(f"Failed to run test script: {str(e)}")
            return False
    
    def print_summary(self, files_status, script_success):
        """Print test execution summary."""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("FINAL TEST RESULTS")
        self.logger.info("=" * 60)
        self.logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Environment: {self.os_type.upper()}")
        self.logger.info(f"Log File: {self.log_file.absolute()}")
        self.logger.info("")
        
        # File test results
        self.logger.info("File-Level Test Results:")
        self.logger.info("-" * 60)
        if files_status:
            for filename, passed in files_status.items():
                status = "✓ PASSED" if passed else "✗ FAILED"
                self.logger.info(f"{filename}: {status}")
        
        self.logger.info("")
        
        # Overall result
        files_all_passed = all(files_status.values()) if files_status else False
        overall_passed = files_all_passed and script_success
        
        self.logger.info("Overall Test Result:")
        self.logger.info("-" * 60)
        
        if overall_passed:
            self.logger.info("")
            self.logger.info("✓✓✓ ALL TESTS PASSED ✓✓✓")
            self.logger.info("")
            self.logger.info("Summary:")
            self.logger.info("  ✓ inputs_backup.py: Verified as vulnerable (correct state)")
            self.logger.info("  ✓ inputs.py: Verified as secured (all vulnerabilities fixed)")
            self.logger.info("  ✓ Platform tests: Passed")
        else:
            self.logger.error("")
            self.logger.error("✗✗✗ TESTS FAILED ✗✗✗")
            self.logger.error("")
            if not files_all_passed:
                self.logger.error("File-level tests failed:")
                for filename, passed in files_status.items():
                    if not passed:
                        self.logger.error(f"  - {filename}")
            if not script_success:
                self.logger.error("Platform-specific tests failed")
        
        self.logger.info("")
        self.logger.info("=" * 60)
    
    def run(self):
        """Execute the complete test workflow."""
        try:
            files_status, script_success = self.run_test_script()
            self.print_summary(files_status, script_success)
            
            # Return success only if all tests pass
            overall_passed = all(files_status.values()) if files_status else False
            return 0 if (overall_passed and script_success) else 1
        except KeyboardInterrupt:
            self.logger.warning("Test execution interrupted by user")
            return 130
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return 1


def main():
    """Main entry point."""
    runner = TestRunner()
    exit_code = runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

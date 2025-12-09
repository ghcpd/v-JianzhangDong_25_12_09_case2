@echo off

set PYTHON_EXE=D:\vscoderprojects\v-JianzhangDong_25_12_09_case2\grok-fast\v-JianzhangDong_25_12_09_case2\.venv\Scripts\python.exe

echo Running security tests...

REM Test 1: SQL Injection in profile endpoint
echo Testing SQL Injection...
for /f %%i in ('%PYTHON_EXE% -c "import requests; r = requests.get('http://127.0.0.1:5000/profile', params={'id': \"' OR 1=1 --\"}); print(r.status_code)"') do set response=%%i
echo Response code: %response%
if "%response%"=="400" (
    echo SQL Injection blocked (secure)
) else (
    echo SQL Injection possible (vulnerable)
    exit /b 1
)

REM Test 2: Command Injection in export endpoint
echo Testing Command Injection...
for /f %%i in ('%PYTHON_EXE% -c "import requests; r = requests.get('http://127.0.0.1:5000/export', params={'name': 'test; echo hacked'}); print(r.status_code)"') do set response=%%i
if "%response%"=="400" (
    echo Command Injection blocked (secure)
) else (
    echo Command Injection possible (vulnerable)
    exit /b 1
)

REM Test 3: Invalid input in auth
echo Testing Auth Input Validation...
for /f %%i in ('%PYTHON_EXE% -c "import requests; r = requests.post('http://127.0.0.1:5000/auth', json={'username':'a'*100}); print(r.status_code)"') do set response=%%i
if "%response%"=="400" (
    echo Auth validation secure
) else (
    echo Auth validation weak
    exit /b 1
)

REM Test 4: SSRF in transfer
echo Testing SSRF...
for /f %%i in ('%PYTHON_EXE% -c "import requests; r = requests.post('http://127.0.0.1:5000/transfer', json={'target':'test','amount':100,'notify_url':'http://internal.com'}); print(r.status_code)"') do set response=%%i
if "%response%"=="400" (
    echo SSRF blocked (secure)
) else (
    echo SSRF possible (vulnerable)
    exit /b 1
)

REM Test 5: Path Traversal in config
echo Testing Path Traversal...
for /f %%i in ('%PYTHON_EXE% -c "import requests; r = requests.post('http://127.0.0.1:5000/config', json={'file':'../../../etc/passwd'}); print(r.status_code)"') do set response=%%i
if "%response%"=="400" (
    echo Path Traversal blocked (secure)
) else (
    echo Path Traversal possible (vulnerable)
    exit /b 1
)

echo All security tests passed
#!/bin/bash

echo "Running security tests..."

# Test 1: SQL Injection in profile endpoint
echo "Testing SQL Injection..."
response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000/profile?id=' OR 1=1 --")
if [ "$response" -eq 400 ]; then
    echo "SQL Injection blocked (secure)"
else
    echo "SQL Injection possible (vulnerable)"
    exit 1
fi

# Test 2: Command Injection in export endpoint
echo "Testing Command Injection..."
response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000/export?name=test; echo hacked")
if [ "$response" -eq 400 ]; then
    echo "Command Injection blocked (secure)"
else
    echo "Command Injection possible (vulnerable)"
    exit 1
fi

# Test 3: Invalid input in auth
echo "Testing Auth Input Validation..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"username":"a"*100}' http://localhost:5000/auth)
if [ "$response" -eq 400 ]; then
    echo "Auth validation secure"
else
    echo "Auth validation weak"
    exit 1
fi

# Test 4: SSRF in transfer
echo "Testing SSRF..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"target":"test","amount":100,"notify_url":"http://internal.com"}' http://localhost:5000/transfer)
if [ "$response" -eq 400 ]; then
    echo "SSRF blocked (secure)"
else
    echo "SSRF possible (vulnerable)"
    exit 1
fi

# Test 5: Path Traversal in config
echo "Testing Path Traversal..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"file":"../../../etc/passwd"}' http://localhost:5000/config)
if [ "$response" -eq 400 ]; then
    echo "Path Traversal blocked (secure)"
else
    echo "Path Traversal possible (vulnerable)"
    exit 1
fi

echo "All security tests passed"
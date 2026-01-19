import re
import sys
import json

# A set of simple static checks against an input filename. Exit code 0 = pass, 1 = fail.

def find_hardcoded_secrets(text):
    patterns = [r"PAYMENT_TOKEN\s*=\s*\".+\"", r"MAIL_SERVER_KEY\s*=\s*\".+\"",
                r"INTERNAL_AUTH\s*=\s*\".+\""]
    matches = []
    for p in patterns:
        for m in re.finditer(p, text):
            matches.append((m.start(), m.group(0)))
    return matches


def find_md5_usage(text):
    if "hashlib.md5(" in text:
        return True
    return False


def find_sql_injection(text):
    # crude detection for string formatted SQL where variables are injected
    if re.search(r"%\s*\w+\s*%", text):
        # not reliable but check for "'%s' % uid" patterns
        if "WHERE id = '%s'" in text or "% uid" in text:
            return True
    # f-string use in SQL
    if re.search(r"f\".*SELECT.*\{.*\}.*\"", text):
        return True
    return False


def find_ssrf_and_request_issues(text):
    problems = []
    # requests.post with token in JSON
    for m in re.finditer(r"requests\.post\(([^)]*)\)", text):
        call = m.group(1)
        if "PAYMENT_TOKEN" in call or "token" in call:
            problems.append('requests.post contains token or PAYMENT_TOKEN')
        if "timeout" not in call:
            problems.append('requests.post without timeout')
    return problems


def find_file_open_from_user(text):
    # open(path) or request.json.get("file") usage
    if "with open(path)" in text or "request.json.get(\"file\")" in text:
        return True
    return False


def find_shell_subprocess(text):
    # subprocess.Popen(..., shell=True) or string-built commands
    if "subprocess.Popen(" in text and "shell=True" in text:
        return True
    if "zip " in text and "subprocess" in text:
        return True
    return False


def find_debug_mode(text):
    if "app.run(debug=True)" in text:
        return True
    return False


def find_print_logging_sensitive(text):
    # Print in transfer funds area
    if re.search(r"print\(.*transfer:.*\)", text):
        return True
    return False


def run_checks(text):
    issues = []
    hc = find_hardcoded_secrets(text)
    if hc:
        issues.append({"id": "hardcoded_secrets", "matches": hc})
    if find_md5_usage(text):
        issues.append({"id": "weak_hash", "matches": "hashlib.md5"})
    if find_sql_injection(text):
        issues.append({"id": "sql_injection", "matches": "string-formatted SQL"})
    ssrf = find_ssrf_and_request_issues(text)
    if ssrf:
        issues.append({"id": "ssrf_requests", "matches": ssrf})
    if find_file_open_from_user(text):
        issues.append({"id": "arbitrary_file_read", "matches": "open(path) from user input"})
    if find_shell_subprocess(text):
        issues.append({"id": "command_injection", "matches": "subprocess with shell or zip via shell"})
    if find_debug_mode(text):
        issues.append({"id": "debug_mode", "matches": "app.run(debug=True)"})
    if find_print_logging_sensitive(text):
        issues.append({"id": "sensitive_logging", "matches": "print transfer logs"})
    return issues


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: check_file.py <file_to_check>")
        sys.exit(2)
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    issues = run_checks(text)
    result = {"file": path, "passed": (len(issues) == 0), "issues": issues}
    print(json.dumps(result, indent=2))
    sys.exit(0 if len(issues) == 0 else 1)

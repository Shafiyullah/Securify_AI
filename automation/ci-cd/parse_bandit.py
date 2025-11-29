import json
import sys
import os

REPORT_FILE = os.environ.get("BANDIT_REPORT", "bandit-report.json")
MIN_SEVERITY_TO_FAIL = ["HIGH", "CRITICAL"]

print(f"Parsing Bandit SAST report: {REPORT_FILE}")

try:
    with open(REPORT_FILE, 'r') as f:
        report = json.load(f)
except FileNotFoundError:
    print(f"Error: Bandit report file '{REPORT_FILE}' not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: Could not parse {REPORT_FILE} as JSON.")
    sys.exit(1)

results = report.get('results', [])
high_or_critical_issues = []

for issue in results:
    if issue['issue_severity'] in MIN_SEVERITY_TO_FAIL:
        high_or_critical_issues.append(issue)

if high_or_critical_issues:
    print(f"\n--- 🚨 SECURITY GATE FAILED! 🚨 ---")
    print(f"Found {len(high_or_critical_issues)} {MIN_SEVERITY_TO_FAIL} severity issues:")
    for issue in high_or_critical_issues:
        print(f"  - [ ] Issue: {issue['issue_text']}")
        print(f"  - [ ] File: {issue['filename']}")
        print(f"  - [ ] Line: {issue['line_number']}\n")
    
    sys.exit(1) # Fail the CI pipeline
else:
    print("\n--- ✅ SECURITY GATE PASSED! ---")
    print("No HIGH or CRITICAL severity issues found.")
    sys.exit(0)
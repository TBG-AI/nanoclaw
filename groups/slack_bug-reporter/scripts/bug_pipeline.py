#!/usr/bin/env python3
"""
Bug Detection & GitHub Issue Pipeline

Full workflow:
1. Query Grafana Cloud for 5xx errors (metrics + logs)
2. Group and deduplicate errors by type + endpoint
3. Check for existing open GitHub issues (avoid duplicates)
4. Create GitHub issues in the correct repo with standardized format

Usage:
    python3 scripts/bug_pipeline.py scan --minutes 60
    python3 scripts/bug_pipeline.py scan --minutes 1440 --dry-run
    python3 scripts/bug_pipeline.py scan --minutes 60 --create-issues
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Add parent dir so we can import grafana_query
sys.path.insert(0, os.path.dirname(__file__))
from grafana_query import GrafanaClient


BACKEND_SERVER_REPO = "TBG-AI/Backend-Server"
BACKEND_ODDS_REPO = "TBG-AI/Backend-Odds"

# Keywords that indicate the error belongs in the odds repo
ODDS_KEYWORDS = [
    "oddsmicroservice",
    "odds-microservice",
    "odds_client",
    "get_parlay_odds",
    "get_odds",
    "odds microservice",
    "odds service",
]


def determine_repo(error_type, error_message, stack_trace, endpoint, service=""):
    """Determine which GitHub repo this bug belongs to."""
    # Direct service match
    if service == "backend-odds":
        return BACKEND_ODDS_REPO
    if service == "backend-server":
        # Still check if error originates from odds microservice
        search_text = f"{error_type} {error_message} {stack_trace} {endpoint}".lower()
        for keyword in ODDS_KEYWORDS:
            if keyword.lower() in search_text:
                return BACKEND_ODDS_REPO
        return BACKEND_SERVER_REPO
    # Fallback: keyword matching
    search_text = f"{error_type} {error_message} {stack_trace} {endpoint}".lower()
    for keyword in ODDS_KEYWORDS:
        if keyword.lower() in search_text:
            return BACKEND_ODDS_REPO
    return BACKEND_SERVER_REPO


def get_bug_label(repo):
    """Get the correct bug label for each repo."""
    return "Bug" if repo == BACKEND_SERVER_REPO else "bug"


def check_duplicate_issue(repo, search_term):
    """Check if an open issue already exists for this error."""
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "open",
             "--search", search_term, "--json", "number,title,url", "--limit", "5"],
            capture_output=True, text=True, timeout=15,
        )
        if result.stdout.strip():
            issues = json.loads(result.stdout)
            return issues
    except Exception:
        pass
    return []


def create_github_issue(repo, title, body, label):
    """Create a GitHub issue."""
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", repo,
         "--title", title, "--label", label, "--body", body],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return f"ERROR: {result.stderr.strip()}"


def group_errors(errors):
    """Group errors by (service, error_type, endpoint) and deduplicate."""
    groups = {}
    for e in errors:
        key = (e.get("service", "unknown"), e.get("error_type", "Unknown"), e.get("endpoint", "unknown"))
        if key not in groups:
            groups[key] = {
                "service": e.get("service", "unknown"),
                "error_type": e.get("error_type", "Unknown"),
                "endpoint": e.get("endpoint", "unknown"),
                "error_message": e.get("error_message", ""),
                "stack_trace": e.get("stack_trace", ""),
                "file": e.get("file", "?"),
                "function": e.get("function", "?"),
                "line_number": e.get("line_number", "?"),
                "environment": e.get("environment", "?"),
                "occurrences": [],
                "trace_ids": [],
            }
        groups[key]["occurrences"].append(e.get("timestamp", "?"))
        trace_id = e.get("trace_id", "")
        if trace_id and trace_id != "?" and trace_id not in groups[key]["trace_ids"]:
            groups[key]["trace_ids"].append(trace_id)
    return groups


def format_issue_title(error_type, endpoint):
    """Generate a standardized issue title."""
    return f"[BUG] {error_type} at {endpoint}"


def format_issue_body(group, minutes):
    """Generate a standardized issue body."""
    count = len(group["occurrences"])
    first_seen = min(group["occurrences"]) if group["occurrences"] else "?"
    last_seen = max(group["occurrences"]) if group["occurrences"] else "?"

    # Extract app-specific stack frames
    app_frames = ""
    if group["stack_trace"]:
        frames = [l.strip() for l in group["stack_trace"].split("\n")
                  if l.strip() and "/app/" in l]
        if frames:
            app_frames = "\n".join(f"    {f}" for f in frames[-8:])

    # Build trace ID list (max 5)
    trace_list = ""
    for tid in group["trace_ids"][:5]:
        trace_list += f"- `{tid}`\n"
    if len(group["trace_ids"]) > 5:
        trace_list += f"- ... and {len(group['trace_ids']) - 5} more\n"

    body = f"""## Bug Report (Auto-generated)

**Source**: Grafana Cloud monitoring (Loki logs)
**Generated at**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Time window**: Last {minutes} minutes

---

### Error Summary

| Field | Value |
|-------|-------|
| **Error Type** | `{group['error_type']}` |
| **Endpoint** | `{group['endpoint']}` |
| **Occurrences** | {count} |
| **First seen** | {first_seen} |
| **Last seen** | {last_seen} |
| **Environment** | {group['environment']} |

### Error Message

```
{group['error_message'][:500]}
```

### Source Location

```
{group['file']}:{group['line_number']} in {group['function']}()
```

### Stack Trace (App Frames)

```python
{app_frames if app_frames else 'No app-specific stack frames available'}
```

### Trace IDs (for Grafana Tempo)

{trace_list if trace_list else 'No trace IDs available'}

### Full Stack Trace

<details>
<summary>Click to expand</summary>

```
{group['stack_trace'][:3000] if group['stack_trace'] else 'Not available'}
```

</details>

---

*This issue was automatically created by the bug-reporter agent from Grafana Cloud error monitoring.*
"""
    return body


def scan_metrics_for_500s(client, minutes=60):
    """Detect 500 errors from OTEL metrics (catches silent errors with no logs)."""
    resp = client.get_error_count_by_endpoint(minutes=minutes)
    parsed = client.parse_metric_result(resp)
    metric_errors = []
    for r in parsed:
        if r["value"] > 0:
            metric_errors.append({
                "service": r["labels"].get("service_name", "unknown"),
                "endpoint": r["labels"].get("http_target", "unknown"),
                "status_code": r["labels"].get("http_status_code", "500"),
                "count": int(r["value"]),
            })
    return metric_errors


def scan_and_report(minutes=60, create_issues=False, dry_run=False):
    """Main pipeline: scan for errors and optionally create GitHub issues."""
    client = GrafanaClient()

    print(f"Scanning for 500 errors in the last {minutes} minutes...")

    # 1a. Get error logs (catches logged exceptions)
    resp = client.get_recent_500_errors(minutes=minutes, limit=100)
    errors = client.parse_error_logs(resp)

    # 1b. Get metric-based 500s (catches silent errors with no logs)
    metric_500s = scan_metrics_for_500s(client, minutes=minutes)
    if metric_500s:
        # Find endpoints with metric 500s but no corresponding log errors
        logged_endpoints = {(e.get("service", ""), e.get("endpoint", "")) for e in errors}
        for m in metric_500s:
            ep = m["endpoint"]
            svc = m["service"]
            if (svc, ep) not in logged_endpoints and ep != "unknown":
                # Create synthetic error entries for metric-only 500s
                errors.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "ERROR",
                    "message": f"Silent 500 detected via metrics on {ep} ({m['count']} occurrences)",
                    "file": "?",
                    "function": "?",
                    "line_number": "?",
                    "trace_id": "?",
                    "span_id": "?",
                    "error_type": "HTTP500",
                    "error_message": f"{m['count']} 500 responses on {ep} in last {minutes}m (no error logs found — silent failure)",
                    "stack_trace": "",
                    "endpoint": ep,
                    "scope": "",
                    "environment": "prod",
                    "service": svc,
                })
                print(f"  [METRICS] {svc} {ep}: {m['count']} silent 500s detected")

    if not errors:
        print("No 500 errors found. All clear!")
        return {"errors": [], "metric_summary": metric_500s}

    print(f"Found {len(errors)} error log entries.")

    # 2. Group and deduplicate
    groups = group_errors(errors)
    print(f"Grouped into {len(groups)} unique error patterns.\n")

    results = []

    for (service, error_type, endpoint), group in sorted(
        groups.items(), key=lambda x: len(x[1]["occurrences"]), reverse=True
    ):
        count = len(group["occurrences"])
        repo = determine_repo(
            error_type, group["error_message"], group["stack_trace"], endpoint, service
        )
        title = format_issue_title(error_type, endpoint)
        label = get_bug_label(repo)

        print(f"{'='*60}")
        print(f"  Error: {error_type}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Count: {count}")
        print(f"  Repo: {repo}")
        print(f"  Title: {title}")

        result = {
            "error_type": error_type,
            "endpoint": endpoint,
            "count": count,
            "repo": repo,
            "title": title,
        }

        if create_issues or dry_run:
            # Check for duplicates first
            search_term = f"{error_type} {endpoint}"
            existing = check_duplicate_issue(repo, search_term)

            if existing:
                print(f"  SKIP: Duplicate issue found: {existing[0].get('title', '?')}")
                print(f"        URL: {existing[0].get('url', '?')}")
                result["status"] = "skipped_duplicate"
                result["existing_url"] = existing[0].get("url", "")
            elif dry_run:
                print(f"  DRY RUN: Would create issue in {repo}")
                body = format_issue_body(group, minutes)
                result["status"] = "dry_run"
                result["body_preview"] = body[:200]
            else:
                body = format_issue_body(group, minutes)
                url = create_github_issue(repo, title, body, label)
                print(f"  CREATED: {url}")
                result["status"] = "created"
                result["url"] = url
        else:
            result["status"] = "detected"

        results.append(result)
        print()

    return {"errors": results, "metric_summary": metric_500s}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bug Detection & GitHub Issue Pipeline")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("scan", help="Scan for errors and optionally create issues")
    p.add_argument("--minutes", type=int, default=60, help="Time window in minutes")
    p.add_argument("--create-issues", action="store_true", help="Create GitHub issues")
    p.add_argument("--dry-run", action="store_true", help="Show what would be created")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "scan":
        result = scan_and_report(
            minutes=args.minutes,
            create_issues=args.create_issues,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

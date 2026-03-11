# Bug Fixer Detailed Workflow

## Step 1: Find Bugs to Fix

```bash
gh issue list --repo TBG-AI/Backend-Server --state open --label "Bug" --json number,title,url,body
gh issue list --repo TBG-AI/Backend-Odds --state open --label "bug" --json number,title,url,body
```

## Step 2: Read and Understand the Issue

Bug-reporter issues have this format:
- **Error Type**: The Python exception class (e.g., `OddsMicroserviceRequestError`)
- **Endpoint**: The API route that failed (e.g., `/main/bets/generate_bet`)
- **Error Message**: What went wrong
- **Source Location**: File, line number, function
- **Stack Trace**: Full and app-filtered versions
- **Trace IDs**: For Grafana Tempo correlation
- **Occurrence Count**: How many times it happened

## Step 3: Clone/Pull and Create Fix Branch

```bash
# First time — clone into workspace
cd /workspace/group
git clone https://github.com/TBG-AI/Backend-Server.git
git clone https://github.com/TBG-AI/Backend-Odds.git

# Subsequent runs — pull latest
cd /workspace/group/Backend-Server && git checkout dev && git pull origin dev
cd /workspace/group/Backend-Odds && git checkout dev && git pull origin dev

# Create fix branch
git checkout -b fix/<issue-number>-<short-description>
```

## Step 4: Investigate Root Cause

1. Go to the source file mentioned in the issue
2. Read the stack trace bottom-up to understand the call chain
3. Identify why the exception is thrown
4. Check if it's a code bug, config issue, or dependency problem

## Step 5: Determine Grouping

Before creating a PR, check if multiple open issues are related:
- Same root cause → group in one PR
- Same component but different causes → separate PRs
- Different components → always separate PRs

## Step 6: Fix and Commit

```bash
git add <files>
git commit -m "Fix: <description>

Fixes #<issue-number>"
```

## Step 7: Create PR

```bash
gh pr create --repo TBG-AI/Backend-Server --base dev \
  --title "Fix: <description>" \
  --body "$(cat <<'EOF'
## Summary
<1-2 sentences explaining the fix>

## Root Cause
<What caused the bug>

## Changes
- <list of changes>

## Testing
- <how to verify the fix>

Fixes #<issue-number>
EOF
)"
```

## Step 8: Report to Channel
Post summary with: which issues fixed, PR URL, brief explanation

## Key Code Locations (Backend-Server)

| Area | File |
|------|------|
| Exception handlers | `src/backend_server/app.py` (lines 216-407) |
| Error mapping | `src/backend_server/infrastructure/api/rest/constants.py` |
| Odds client | `src/backend_server/infrastructure/microservices/odds_client.py` |
| Bet service | `src/backend_server/application/services/bets/user_bet_service.py` |
| Bet routes | `src/backend_server/infrastructure/api/rest/bet_routes.py` |
| Metrics middleware | `src/backend_server/infrastructure/middleware/metrics_middleware.py` |
| Request ID middleware | `src/backend_server/infrastructure/middleware/request_id.py` |
| Logging formatter | `src/backend_server/logging_formatter.py` |

## Grafana Tools (for additional investigation)

```bash
# Get full trace details
python3 /workspace/group/scripts/grafana_query.py trace <trace_id>

# Get request logs
python3 /workspace/group/scripts/grafana_query.py request <request_id>
```

## Historical Fixes
- 2026-03-03: OddsMicroserviceRequestError 500s + 25x odds (issue #68) — deployed task def 107, verified clean, issue closed

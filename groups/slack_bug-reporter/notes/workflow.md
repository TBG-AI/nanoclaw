# Bug Reporter Workflow

## Step-by-Step Process

### 1. Detect Errors
```bash
python3 /workspace/group/scripts/grafana_query.py error-rate
python3 /workspace/group/scripts/grafana_query.py error-count --minutes 60
```
If error rate > 0 or error count > 0, proceed to investigate.

### 2. Get Error Details
```bash
python3 /workspace/group/scripts/grafana_query.py errors --minutes 60 --limit 50
```
This shows: error type, endpoint, stack trace, trace IDs, source file location.

### 3. Investigate with Traces (optional, for deeper analysis)
```bash
python3 /workspace/group/scripts/grafana_query.py trace <trace_id>
```

### 4. Create GitHub Issues
```bash
# Dry run first
python3 /workspace/group/scripts/bug_pipeline.py scan --minutes 60 --dry-run

# If looks good, create issues
python3 /workspace/group/scripts/bug_pipeline.py scan --minutes 60 --create-issues
```

### 5. Report to Channel
Post summary with:
- Current error rate
- Number of unique error patterns
- For each pattern: error type, endpoint, count, severity
- Which repos got issues (with URLs)
- Root cause analysis if possible

## Routing Logic

| Error Pattern | Target Repo |
|---|---|
| OddsMicroserviceRequestError | TBG-AI/Backend-Odds |
| Error message mentions "odds-microservice" | TBG-AI/Backend-Odds |
| Stack trace includes "odds_client" | TBG-AI/Backend-Odds |
| Everything else | TBG-AI/Backend-Server |

## Issue Deduplication
Before creating an issue, the pipeline searches for open issues with the same error type + endpoint.
If a matching open issue exists, it skips creation and logs the existing issue URL.

## Report Format (what a good report looks like)

```
*Bug Report — Last 60 Minutes*
• Error rate: 0.81 req/s

*Bug 1: OddsMicroserviceRequestError at /main/bets/generate_bet — CRITICAL*
• Count: ~17,274
• Error: Client error '422 Unprocessable Entity'
• Call chain: bet_routes.py:59 → user_bet_service.py:343 → odds_client.py:58
• Root cause: Backend-Odds returning 422 on /odds/get_parlay_odds
• Issue: https://github.com/TBG-AI/Backend-Server/issues/482

*Bug 2: HTTP 500 at /main/transactions_v1/paypal/create-order — HIGH*
• Count: ~988
• Logs: No error-level logs — completely silent 500s
• Root cause: Exception caught but not logged before returning 500
```

## Severity Classification
- *CRITICAL*: > 1000 occurrences or actively failing at high rate
- *HIGH*: 100-1000 occurrences
- *MEDIUM*: 10-100 occurrences
- *LOW*: < 10 occurrences or transient

## Historical Context
- 2026-03-02: Scripts created by senior-developer
- 2026-03-03: First automated scan — OddsMicroserviceRequestError at /bets/generate_bet (28x), HTTPException at /users/kyc/session (1x)
- 2026-03-03: Issue #482 created, OddsMicroserviceRequestError resolved (task def 107)
- 2026-03-10: Ongoing — generate_bet (17K+ 500s), PayPal create-order (988 silent 500s)

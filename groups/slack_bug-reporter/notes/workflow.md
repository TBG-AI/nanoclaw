# BugReporter workflow

Step-by-step procedure for a scan. Run this on demand (`@BugReporter scan last 24h`) or on schedule.

## Phase 1 — Health check

```bash
python3 /workspace/group/scripts/grafana_query.py error-rate
```

**Interpret**:
- Any service > 1% error rate → HIGH priority scan
- Any service > 5% error rate → CRITICAL, post alert to channel immediately, then continue
- All services green → proceed with normal scan, don't post unless findings

## Phase 2 — Fetch error logs

```bash
python3 /workspace/group/scripts/grafana_query.py errors --minutes 1440   # 24h
```

This uses `GrafanaClient.get_error_logs()` which pulls from Loki with the filter:
```logql
{service=~"backend-server|backend-odds"} |= "ERROR" | json
```

**Required fields** (per TbgJsonFormatter schema — all Loki lines should have these):
- `ts`, `level`, `msg`, `service`, `env`
- `request_id`, `session_id`, `user_id` (when available)
- `flow`, `flow_step` (when set)
- `err.type`, `err.msg`, `err.stack` (for exceptions)
- `module`, `func`, `line`

If any field is missing from the logs, **flag a structured-logging gap** — file a `needs-instrumentation` issue against the service.

## Phase 3 — Group by signature

Error signature = `(error_type, endpoint, top_tbg_frame, flow)`.

Group the raw logs by this tuple. For each group, compute:
- `occurrences` — count of log lines in the group
- `first_seen`, `last_seen` — min/max `ts`
- `affected_users` — `len(set(user_id for log in group if user_id))`
- `sample_request_ids` — up to 3 recent `request_id`s
- `sample_trace_ids` — up to 3 recent `trace_id`s (from OTEL span attributes if available)
- `endpoint_total_requests` — total requests to the endpoint in the window (from Prom)
- `blast_radius` — `occurrences / endpoint_total_requests * 100`

## Phase 4 — Severity & routing

Apply the severity matrix (handoff contract §A). Then route:

```python
def route(group):
    svc = group["service"]
    text = f"{group['error_type']} {group['err_msg']} {group['stack']} {group['endpoint']}".lower()
    odds_keywords = ["oddsmicroservice", "odds-microservice", "odds_client",
                     "get_parlay_odds", "get_odds", "odds service"]
    if svc == "backend-odds" or any(k in text for k in odds_keywords):
        return "TBG-AI/Backend-Odds"
    return "TBG-AI/Backend-Server"
```

## Phase 5 — Dedup (MANDATORY before create)

For each group, run:

```bash
gh issue list --repo <repo> --state open \
  --search "{error_type} {endpoint}" \
  --json number,title,body,createdAt,updatedAt
```

**Match rules** (ALL must hold):
1. Same `error_type` in title OR body
2. Same `endpoint` in body frontmatter
3. Same top TBG-owned frame (file + line ±5)
4. Same `flow`

If matched → **UPDATE** via `gh issue comment` with the template in handoff §A. Do NOT create.
If not matched → proceed to Phase 6.

## Phase 6 — Create issue

Build the body from the template (handoff contract §A). Create:

```bash
gh issue create --repo <repo> \
  --title "[BUG] {error_type} at {endpoint}" \
  --label "Bug,severity:{sev},flow:{domain},needs-fixer" \
  --body-file /tmp/issue-body.md
```

**After creation**:
- Store `issue_number` → `(error_type, endpoint, flow)` mapping in `notes/issue-map.json` for future dedup
- Append to `notes/scan-history.md`

## Phase 7 — Regression check

For each newly-created issue:

```bash
gh issue list --repo <repo> --state closed \
  --search "{error_type} {endpoint}" \
  --json number,title,closedAt \
  --limit 5
```

If a closed issue with the same signature was closed within the last 30 days:
- Add the `suspected-regression` label to the new issue
- Link the prior PR in the new issue body
- Ping `#agentic-dev` with `:rotating_light: suspected regression`

## Phase 8 — Report

Post the Slack summary (template in main CLAUDE.md). Include:
- Counts: new + updated + critical
- Top 3 by severity
- Dashboard link
- Regression alerts (if any)

## Phase 9 — Self-audit

Append to `notes/scan-history.md`:

```markdown
## 2026-04-09T14:30:00Z — 24h scan
- Window: 1440m
- Error rate: backend-server 0.8%, backend-odds 0.3%
- New issues: 3 (1 CRITICAL, 2 HIGH)
- Updated: 1 (#1201 +340 occ)
- Regressions: 0
- Duration: 47s
- Notes: NullOddsError is new — not in scan-history before
```

## Failure modes & what to do

| Failure | Action |
|---|---|
| Grafana returns 5xx | Retry once with 30s backoff. If still failing, post `BugReporter offline — Grafana unreachable` and stop. |
| `GRAFANA_SA_TOKEN` missing | Post `BugReporter needs GRAFANA_SA_TOKEN — please set and restart`. Exit. |
| GitHub rate limit | Back off exponentially, max 3 retries. If still failing, defer issue creation and post to channel. |
| Structured-logging gap (missing required fields) | File `needs-instrumentation` issue against the service. Do not skip — log debt compounds. |
| Flow name not in `flow-registry.json` | Use `flow:unknown` label and note in scan report. Flag for the platform team. |
| Dedup uncertain (borderline match) | Err on the side of UPDATE. Creating duplicates is worse than over-merging. |

---
name: debug-logs
description: Query TBG structured logs, metrics, and traces via Grafana Cloud. Use for reproducing bugs, investigating errors, correlating requests across services, and verifying fixes post-deploy. Supports queries by request_id, trace_id, error_type, endpoint, flow, or time window. Writes audit reports to outputs/. Distinct from /tbg-logs (local dev log files) and /cw-logs (raw CloudWatch tail) — this is the structured, correlation-driven debugging skill for production.
user_invocable: true
---

# Debug Logs

Wraps nanoclaw's `GrafanaClient` to query TBG's structured log pipeline (Loki + Prometheus + Tempo) with correlation-aware queries. This is the **primary debugging tool** for BugFixer, PR review, and any agent investigating production behavior.

> **When NOT to use this skill**:
> - Local development logs → use `/tbg-logs`
> - Raw ECS/CloudWatch tail → use `/cw-logs`
> - Reading source code → use Read/Grep directly
>
> **When TO use this skill**:
> - Reproducing a specific bug from a `trace_id` or `request_id`
> - Investigating an error pattern across a time window
> - Verifying a fix post-deploy (did the error rate drop?)
> - Understanding which users/endpoints/flows a bug affects
> - Correlating logs across Backend-Server ↔ Backend-Odds

## Prerequisites

`GRAFANA_SA_TOKEN` is stored in **AWS SSM** at `/tbg/shared/observability/GRAFANA_SA_TOKEN` (SecureString, us-east-1). Load it before running any `/debug-logs` command.

**Preferred**: load into current shell, then run queries freely:
```bash
source tools/observability/load-token.sh
python3 tools/observability/grafana_query.py error-rate
```

**Inline** (no shell pollution, one command):
```bash
GRAFANA_SA_TOKEN=$(tools/observability/load-token.sh --print) \
  python3 tools/observability/grafana_query.py error-rate
```

If SSM fetch fails (no AWS creds, missing IAM perms, parameter missing), the skill exits 2/3/4 with helpful instructions. Do not attempt to proceed without the token — never hardcode or paste a token into chat (it ends up in conversation history; rotate immediately if you do).

See [`tools/observability/README.md`](../../../tools/observability/README.md) for full setup, rotation, and nanoclaw container integration notes.

The underlying script is `grafana_query.py`. Prefer the stable path:

```bash
python3 tools/observability/grafana_query.py <command> [args]
```

This is a host-side symlink pointing at the real file in `nanoclaw/groups/slack_bug-reporter/scripts/grafana_query.py`. The symlink lets any Dev-Agentic agent import it without knowing nanoclaw's layout, while the real file stays inside nanoclaw so the container runtime is unaffected. See [`tools/observability/README.md`](../../../tools/observability/README.md) for details.

Inside the nanoclaw container (where `@BugReporter` and `@BugFixer` run), the script is at `/workspace/group/scripts/grafana_query.py` — use that path when running from inside the container.

## Commands

### 1. Reproduce by trace ID

```
/debug-logs trace <trace_id>
```

Fetches the full span tree from Tempo for a trace, plus all Loki log lines tagged with that trace_id. Output includes:
- Span hierarchy (which service → which endpoint → which function)
- Duration per span
- Errors (if any) with stack traces
- Cross-service hops (Backend-Server ↔ Backend-Odds)

**Use when**: you have a trace_id from a bug report and need to see exactly what happened.

### 2. All logs for a request

```
/debug-logs request <request_id> [--hours <N>]
```

Fetches every Loki log line tagged with this `request_id` — across both services if the request crossed the boundary. Default window: 24h.

**Use when**: the bug report has a `request_id` but no `trace_id`, or you need to see *all* logs for the request, not just errors.

### 3. Error-type investigation

```
/debug-logs error-type <ExceptionClassName> [--service <svc>] [--window <minutes>] [--limit <N>]
```

Fetches recent occurrences of a specific exception type. Groups by endpoint, shows counts, sample correlation IDs, and affected users.

**Use when**: verifying a fix (did the error count drop to zero?) or scoping the blast radius of a bug.

### 4. Endpoint errors

```
/debug-logs endpoint "<METHOD> <path>" [--window <minutes>] [--service <svc>]
```

Fetches errors for a specific endpoint. Useful when you know *where* the bug is but not *which* exception is firing.

### 5. Flow investigation

```
/debug-logs flow <flow_name> [--window <minutes>]
```

Fetches logs + metrics for a business flow (e.g., `bets.place_parlay`). Uses the `flow` field set by `@flow_traced` decorators.

**Use when**: investigating whether a business flow (not just a single endpoint) is healthy.

### 6. Error rate & latency

```
/debug-logs error-rate [--service <svc>]
/debug-logs p99 [--service <svc>] [--endpoint <path>]
```

Pulls current error rate (Prometheus) and p99 latency for a service or endpoint. Quick health checks.

### 6b. Slow traces (latency investigation)

```
/debug-logs slow-traces [--min-duration-ms <N>] [--limit <N>] [--service <svc>]
/debug-logs slow-endpoints [--window <minutes>]
```

- **`slow-traces`** — fetch trace IDs from Tempo where duration exceeds threshold. Default `min_duration_ms=1000`. Returns the slowest N traces with their endpoints and start times. Use this to find latency bugs that aren't 5xx-ing.
- **`slow-endpoints`** — aggregate Prometheus p95/p99 per endpoint over a window, return the top offenders. Answers "which endpoints are consistently slow?"

Both are used by the latency scan phase of BugReporter (see [`agents/bug-reporter/notes/workflow.md`](../../../agents/bug-reporter/notes/workflow.md) Phase 1b) and the `/bug-pipeline` skill.

**SLO targets** (if you need them for classification):
- User-interactive: p95 < 500ms, p99 < 1.5s
- Write endpoints (bets/payments/auth): p95 < 1s, p99 < 3s
- Read-heavy (leagues/history): p95 < 2s, p99 < 5s
- Internal: p95 < 5s, p99 < 15s

Full SLO rationale in [`TBG-DOCS/plans/06-observability-debugging/reduction-strategy.md`](../../../TBG-DOCS/plans/06-observability-debugging/reduction-strategy.md) §"The 4 buckets of requests".

### 7. 24-hour report (dry-run scan)

```
/debug-logs scan --window 1440
```

Runs the same logic as BugReporter's scan but in read-only mode. Returns a summary of:
- Error rates by service
- Top error types
- Top affected endpoints
- Candidate new issues (not yet filed)

**Use when**: you want BugReporter's view without actually creating GitHub issues.

## Workflow

### Phase 1 — Inputs
Ask the user (only if you truly can't infer):
1. What's the **input**? (trace_id, request_id, error_type, endpoint, or flow)
2. What's the **time window**? Default: 1h for active debugging, 24h for post-deploy verification.
3. Which **service**? Default: both. Narrow if the bug is clearly one-sided.

### Phase 2 — Check prerequisites
```bash
if [ -z "$GRAFANA_SA_TOKEN" ]; then
  echo "Error: GRAFANA_SA_TOKEN not set."
  echo "Get a token from https://vxbrandon00.grafana.net → Service Accounts."
  echo "Then: export GRAFANA_SA_TOKEN=<token>"
  exit 2
fi
```

### Phase 3 — Run the query
Invoke `grafana_query.py` directly. Map the skill command → script subcommand:

| Skill command | Script call |
|---|---|
| `trace <id>` | `grafana_query.py trace <id>` |
| `request <id>` | `grafana_query.py logs-by-request <id>` |
| `error-type X` | `grafana_query.py errors-by-type "X" --minutes N` |
| `endpoint "M /path"` | `grafana_query.py endpoint-errors "M /path" --minutes N` |
| `error-rate` | `grafana_query.py error-rate` |
| `scan` | `grafana_query.py report --minutes N` (read-only) |

### Phase 4 — Parse and present
Don't dump raw JSON at the user. Parse and render:

```markdown
## Debug results: `error-type NullOddsError`

**Window**: last 1h · **Service**: backend-server

### Summary
- **Occurrences**: 47
- **Affected users**: 12 unique
- **Affected endpoints**: 1 (`POST /api/v1/parlays/place`)
- **Flow context**: `bets.place_parlay` · step: `stake_calculation`

### Sample correlation IDs
| request_id | trace_id | timestamp |
|---|---|---|
| `abc123` | `def456` | 2026-04-09T14:12:03Z |
| `abc124` | `def457` | 2026-04-09T14:08:41Z |
| `abc125` | `def458` | 2026-04-09T14:03:17Z |

### Top stack frame
```
File "src/backend_server/application/services/bets/user_bet_service.py", line 284
    stake = sum(leg.odds * leg.amount for leg in parlay.legs)
TypeError: unsupported operand type(s) for *: 'NoneType' and 'Decimal'
```

### Links
- [Loki query](https://vxbrandon00.grafana.net/...)
- [Trace def456 in Tempo](https://vxbrandon00.grafana.net/...)
```

### Phase 5 — Write audit report

Append the structured result to a dated file under `outputs/`:

```
outputs/YYYY-MM-DD-debug-<slug>.md
```

Slug format: `<kind>-<identifier>` where kind ∈ {`trace`, `request`, `errortype`, `endpoint`, `flow`, `scan`} and identifier is a short hash or the input value kebab-cased.

Example: `outputs/2026-04-09-debug-errortype-nulloddserror.md`

Include a YAML front-matter block:
```yaml
---
date: 2026-04-09
kind: debug-logs
agent: claude-opus-4-6
query: error-type NullOddsError
window: 1h
service: backend-server
occurrences: 47
affected_users: 12
status: completed
---
```

Tell the user the path after writing:
```
Audit report saved: outputs/2026-04-09-debug-errortype-nulloddserror.md
```

### Phase 6 — Suggest next actions

Based on the result, propose the next step:

| Result | Next action |
|---|---|
| Found the error + reproduction is clean | Suggest `/pr-review` (if there's an open PR) or hand off to BugFixer |
| Error is still happening post-deploy | Reopen the GitHub issue, restart BugFixer workflow |
| Error dropped to zero | Close the GitHub issue with screenshot |
| No matching logs | Broaden the window, or suggest the trace_id is too old |
| Structured-logging gap (missing fields) | File `needs-instrumentation` issue |

## Hard rules (safety)

1. **Never run in write mode.** This skill READS from Grafana and WRITES only to `outputs/` (local). It never creates/edits/closes GitHub issues — that's BugReporter's and BugFixer's job.
2. **Never print secrets.** `GRAFANA_SA_TOKEN` must never appear in output, logs, or committed files.
3. **Never fabricate trace_ids.** If the query returns nothing, say "no results" — don't invent plausible-looking IDs.
4. **Respect the rate limit.** No more than 10 queries per minute. If the user asks for many queries, batch into a scan instead.
5. **Never overwrite audit reports.** If `outputs/YYYY-MM-DD-debug-<slug>.md` exists, append `-v2`, `-v3`, etc.

## Common usage patterns

### BugFixer reproducing a bug
```
/debug-logs trace abc123def456
```

### Post-deploy fix verification
```
/debug-logs error-type NullOddsError --service backend-server --window 1h
```
Expected: 0 occurrences → fix worked.

### PR reviewer sanity-checking a flow
```
/debug-logs flow bets.place_parlay --window 24h
```

### Daily scan (read-only, no issue creation)
```
/debug-logs scan --window 1440
```

### Correlating a user report
User says "my bet failed at 2pm". Find the request:
```
/debug-logs endpoint "POST /api/v1/bets/place" --window 2h
```
Then drill into a specific request:
```
/debug-logs request <request_id_from_first_query>
```

## Failure modes

| Failure | Message | Exit |
|---|---|---|
| `GRAFANA_SA_TOKEN` unset | Helpful instructions to get & set token | 2 |
| Grafana unreachable | "Grafana unreachable (host=X). Check network/VPN." | 3 |
| Empty result | "No matching logs for {query} in {window}. Try broadening with --window N or checking the input." | 0 |
| Script not found | "grafana_query.py missing at {path}. Run scripts/worktree/install.sh --full to restore nanoclaw files." | 4 |
| Rate limited (429) | Back off 60s, retry once, then fail | 5 |

## Related

- Underlying library: [`nanoclaw/groups/slack_bug-reporter/scripts/grafana_query.py`](../../../nanoclaw/groups/slack_bug-reporter/scripts/grafana_query.py)
- Consumers: [`agents/bug-reporter/`](../../../agents/bug-reporter/), [`agents/bug-fixer/`](../../../agents/bug-fixer/), [`pr-review`](../pr-review/SKILL.md)
- Handoff contract: [`agents/bug-agents-handoff.md`](../../../agents/bug-agents-handoff.md)
- Architecture doc: [`TBG-DOCS/plans/06-observability-debugging/dev-architecture.md`](../../../TBG-DOCS/plans/06-observability-debugging/dev-architecture.md)

---
name: bug-pipeline
description: Run the full bug-detection + bug-fix pipeline end-to-end. Orchestrates BugReporter scan → issue creation → BugFixer reproduction → test-first fix → PR → /pr-review → post-deploy verification, backed by Grafana Cloud via /debug-logs. Use when the user says "run the bug pipeline", "do a full bug scan", "find bugs and fix them", or wants to see what BugReporter + BugFixer would do over a time window. Supports dry-run (no GitHub writes) and live modes.
user_invocable: true
---

# Bug Pipeline

Orchestrates the full bug-detection + bug-fix loop. Composes the existing pieces — `/debug-logs`, `@BugReporter` role, `@BugFixer` role, `/pr-review`, and the handoff contract — into a single command so an operator can run the whole pipeline in one go (dry-run by default).

> **Distinction from siblings**:
> - [`/debug-logs`](../debug-logs/SKILL.md) queries Grafana but doesn't act on the results
> - [`agents/bug-reporter/`](../../../agents/bug-reporter/) is the persistent nanoclaw identity that scans on a schedule
> - [`agents/bug-fixer/`](../../../agents/bug-fixer/) is the persistent identity that resolves issues
> - **This skill** is the *ad-hoc orchestrator* — it lets an operator (or any Claude Code session) fire a one-shot end-to-end run without waiting for the Slack agents

## When to use

- "Run the bug pipeline for the last 48h"
- "Scan prod for bugs and show me what BugReporter would file"
- "Do a full bug-hunt dry-run"
- "Walk me through a complete pipeline run"
- Testing the pipeline during bring-up (this is how the current author dogfoods)

## Hard rules

1. **Default to dry-run.** Never create real GitHub issues unless the user says `--live` or explicitly asks to "create issues".
2. **Never modify source code** — this is an observability + orchestration skill, not a fixer. If the user asks to actually apply a fix, hand off to `/f2-swe` or `/f3-swe` or the manual workflow in [`agents/bug-fixer/notes/workflow.md`](../../../agents/bug-fixer/notes/workflow.md).
3. **Never leak the token.** The Grafana token lives in AWS SSM at `/tbg/shared/observability/GRAFANA_SA_TOKEN`. Always load via `tools/observability/load-token.sh`. Never paste a token into chat, never write it to a file, never log it.
4. **Write the audit report.** Every run produces a dated report at `outputs/YYYY-MM-DD-bugrun-<window>.md`. If a file with that name exists, append `-v2`, `-v3`, etc.
5. **Stop on real errors, not on empty results.** If the 48h scan returns zero findings, that's a success, not a failure. Report it as "clean window" and exit 0.

## Inputs the skill asks for

1. **Time window** (minutes) — default 1440 (24h). Common: 60, 720, 1440, 2880, 10080.
2. **Mode** — `dry-run` (default) | `live` (creates real issues)
3. **Service filter** — `backend-server` | `backend-odds` | `both` (default)
4. **Action after scan** — `report-only` (default) | `walk-through` (pick one finding and trace it through BugFixer's workflow)

Don't interrogate — infer from context. Only ask if truly ambiguous.

## Workflow

### Phase 0 — Pre-flight

```bash
# 1. Load the Grafana token from SSM
source tools/observability/load-token.sh
# (exits 2/3/4 with instructions if SSM fetch fails)

# 2. Quick connectivity check
python3 tools/observability/grafana_query.py error-rate
# Expected: "Current 5xx error rate: X.YZ req/s"

# 3. If the rate is unusually high (>5%), post-alert style header
```

If pre-flight fails, stop and report which step failed. Do not proceed.

### Phase 1 — BugReporter scan (dry-run)

Two parallel scans — errors AND high-latency:

```bash
# ─── Error scan ───
# Prometheus: total error count over the window (sanity check the volume)
python3 tools/observability/grafana_query.py error-count --minutes <WINDOW>

# Loki: fetch actual error log lines (this is what BugReporter groups)
python3 tools/observability/grafana_query.py errors --minutes <WINDOW>

# ─── Latency scan (new) ───
# Prometheus: p95 and p99 per endpoint
python3 tools/observability/grafana_query.py p99 --service backend-server

# Tempo: slow traces (sample 3 per endpoint above SLO threshold)
# Inline Python until grafana_query.py CLI exposes this:
python3 -c "
import sys; sys.path.insert(0, 'tools/observability')
from grafana_query import GrafanaClient
c = GrafanaClient()
slow = c.get_slow_traces(min_duration_ms=1000, limit=200)
for trace in slow.get('traces', [])[:20]:
    print(trace)
"
```

If the Loki query returns "No 500 errors found" BUT Prometheus shows a non-zero count, flag a **structured-logging gap** — the errors are happening but aren't tagged in a way Loki's query catches. Include this in the report as a finding to investigate.

If an endpoint has p95/p99 exceeding SLO but fewer than 50 samples, **suppress** — not enough data.

### Phase 2 — Group + classify (simulate BugReporter's Phase 3–4)

Parse the Loki results. For each group:
- `error_type`, `endpoint`, `file:line`, `flow`
- `occurrences`, `first_seen`, `last_seen`
- `affected_users` (if `user_id` field populated)
- `blast_radius` (occurrences / endpoint total requests)
- `severity` per [handoff contract §A](../../../agents/bug-agents-handoff.md)

### Phase 3 — Dedup against existing issues (dry-run: check only, don't update)

```bash
# For each candidate group:
gh issue list --repo TBG-AI/Backend-Server --state open \
  --search "<error_type> <endpoint>" --json number,title,url
gh issue list --repo TBG-AI/Backend-Odds   --state open \
  --search "<error_type> <endpoint>" --json number,title,url
```

Annotate each group as `new` or `would-update:#<N>`.

### Phase 4 — Print the BugReporter output

Render a Slack-style summary (what would be posted to `#agentic-dev`):

```
*Scan complete — dry-run* — window: last Nh · M candidate issues

*CRITICAL* (count)
• _ErrorType_ at `endpoint` — users, occ · flow: `...` · **[new]** | **[would-update:#N]**

*HIGH* (count)
...

*MEDIUM* (count)
...

*LOW* (count)
...

Dashboard: <grafana-url>
```

### Phase 5 — Optional walk-through (if action=walk-through)

Pick the highest-severity new finding. Walk through what BugFixer would do:

1. **Validate contract**: does the (simulated) issue have all §A fields? List them.
2. **Reproduce**: pick the newest sample `trace_id`:
   ```bash
   python3 tools/observability/grafana_query.py trace <trace_id>
   ```
3. **Locate root cause**: identify the top TBG-owned stack frame
4. **Test-first plan**: describe the failing test that would be written
5. **Fix sketch**: describe the 1–3 line change (do not actually write code)
6. **PR frontmatter**: render the §B template with placeholder values
7. **Verification plan**: the `/debug-logs error-type X --window 1h` query that would confirm the fix

### Phase 6 — Audit report

Write `outputs/YYYY-MM-DD-bugrun-<window>.md` with:

```yaml
---
date: YYYY-MM-DD
kind: bug-pipeline-run
agent: claude-opus-4-6
mode: dry-run | live
window_minutes: N
services: backend-server|backend-odds|both
status: completed | partial | failed
findings:
  critical: N
  high: N
  medium: N
  low: N
  total: N
---
```

Full report body: pre-flight results, raw query outputs, grouped findings, dedup status, Slack summary, walk-through (if requested), next actions.

### Phase 7 — Next-step suggestions

Based on findings, tell the user what to do next:

| Finding count | Suggested next action |
|---|---|
| 0 critical + 0 new | "Clean window. No action needed." |
| ≥1 critical | "Run live mode to create the issues, or investigate top finding manually first." |
| ≥1 would-update | "Existing issues will be updated with new occurrence counts on the next real scan." |
| Loki gap detected | "File a `needs-instrumentation` issue — Prom sees errors Loki doesn't." |

## Output format (what the user sees in chat)

Lead with the summary table, not the raw Grafana output. Example:

```
## Pipeline run — 48h dry-run

**Pre-flight**: ✓ token loaded, Grafana reachable, error rate 0.003 req/s

**Scan**:
- Prometheus: 1,247 5xx errors over 2,880m
- Loki: 89 error log lines retrieved
- Grouped into 4 candidate issues

**Findings** (dry-run, no issues created):
| # | Severity | Error | Endpoint | Occ | Users | Status |
|---|---|---|---|---|---|---|
| 1 | HIGH | NullOddsError | POST /api/v1/parlays/place | 47 | 12 | new |
| 2 | MEDIUM | ConnectionTimeout | GET /internal/markets | 2403 | — | new |
| 3 | LOW | KeyError session_id | GET /api/v1/me | 8 | 8 | would-update:#1198 |
| 4 | LOW | ValidationError | POST /api/v1/users/register | 23 | 12 | new |

**Audit report**: `outputs/2026-04-09-bugrun-48h.md`

**Next**: review finding #1 (HIGH) or run with `--live` to create issues.
```

## Failure modes

| Failure | Handling |
|---|---|
| SSM fetch fails | Stop. Instructions to provision token. Don't attempt Grafana. |
| Grafana unreachable | Stop. "Grafana unreachable — check network/VPN". |
| Loki returns empty but Prom has count | Flag structured-logging gap. Continue, note in report. |
| bug_pipeline.py not found | "Run ./scripts/worktree/install.sh --full to clone nanoclaw first." |
| Empty window (no errors anywhere) | Success. Report "clean window". Exit 0. |
| gh CLI not authenticated | Warn, skip dedup step, proceed with all findings marked `new?`. |

## Related

- [`/debug-logs`](../debug-logs/SKILL.md) — individual Grafana queries (this skill composes them)
- [`agents/bug-reporter/CLAUDE.md`](../../../agents/bug-reporter/CLAUDE.md) — scheduled scanner role (this skill is the ad-hoc equivalent)
- [`agents/bug-fixer/CLAUDE.md`](../../../agents/bug-fixer/CLAUDE.md) — fix workflow (walk-through mode simulates it)
- [`agents/bug-agents-handoff.md`](../../../agents/bug-agents-handoff.md) — the contract this skill satisfies
- [`/pr-review`](../pr-review/SKILL.md) — consumes the PR this pipeline would produce
- [`TBG-DOCS/plans/06-observability-debugging/`](../../../TBG-DOCS/plans/06-observability-debugging/README.md) — workstream docs
- [`tools/observability/load-token.sh`](../../../tools/observability/load-token.sh) — SSM token loader

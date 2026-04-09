# Bug agents handoff contract

The **wire format** between `@BugReporter` and `@BugFixer`. This is the contract — both agents MUST satisfy their side. If either agent deviates, the whole pipeline degrades silently.

> **Why this exists**: before this contract, reporter and fixer communicated via freeform GitHub issue bodies. The fixer had to re-derive context the reporter already knew (trace IDs, flow names, affected users), and fixes routinely missed the root cause because the issue didn't include enough correlation info. This contract fixes that by **making structured context mandatory**.

---

## The handoff

```
                   ┌──────────────────┐
   Grafana alerts  │                  │   Issue + full context
  ────────────────▶│  @BugReporter    │──────────────────────▶ GitHub Issue
   (Loki / Prom /  │                  │   (structured, per    (Backend-Server
    Tempo)         └──────────────────┘    this contract §A)   or Backend-Odds)
                                                                    │
                                                                    ▼
                   ┌──────────────────┐   Reads issue,     ┌──────────────────┐
                   │                  │   reproduces,       │                  │
   dev branch  ◀───│   @BugFixer      │◀────────────────────│  GitHub Issue    │
    PR         ───▶│                  │   test → fix →      │  (with trace_id, │
                   └──────────────────┘   PR per §B          │   flow, repro)   │
                                                              └──────────────────┘
                                                                    │
                                                              PR review via
                                                               /pr-review skill
```

---

## §A — Issue format (BugReporter's output)

Every issue BugReporter creates **MUST** contain these fields. Missing any field is a contract violation — downstream agents will refuse to act on a malformed issue.

### Required frontmatter (at the top of the issue body)

```markdown
<!-- tbg-bug-report -->
**Error type**: `{ExceptionClassName}`
**Service**: `backend-server` | `backend-odds`
**Flow**: `{flow_name}` · step: `{flow_step}` · _(from flow-registry.json)_
**Endpoint**: `{METHOD} {path}`
**First seen**: `{iso8601}` · **Last seen**: `{iso8601}`
**Occurrences**: `{int}` over `{window_minutes}`m
**Affected users**: `{int}` unique user_ids · _(from Loki count by user_id_ctx)_
**Severity**: `CRITICAL | HIGH | MEDIUM | LOW`
**Blast radius**: `{percent}%` of requests to this endpoint
```

### Required sections

1. **Sample correlation IDs** — up to 3 recent `request_id` + `trace_id` pairs. Fixer uses these to reproduce via `/debug-logs`.
2. **Error message** — the exact `err.msg` field from the log entry.
3. **Top stack frame** — first TBG-owned frame (not stdlib / not third-party).
4. **Full stack trace** — in a collapsible `<details>` block.
5. **Grafana links**:
   - Loki query (pre-filled with `{error_type}` and time window)
   - Tempo trace view (using one of the sample `trace_id`s)
   - Prometheus error rate panel for the affected endpoint
6. **Related issues** — links to any open issues with the same `error_type` on the same endpoint (if dedup didn't match fully).
7. **Suggested owner** — BugFixer, or a specific skill (F-2, F-3, daily-refactor).

### Severity classification

| Severity | Trigger | SLA |
|---|---|---|
| **CRITICAL** | `affected_users > 100` OR `blast_radius > 50%` OR flow is `payment.*` / `auth.*` | Fix within 2h |
| **HIGH** | `occurrences > 1000/h` OR `affected_users > 20` | Fix within 24h |
| **MEDIUM** | `occurrences > 100/h` OR `blast_radius > 5%` | Fix within 1 week |
| **LOW** | `occurrences < 100/h` AND `affected_users < 5` | Triage weekly |

Note: the old plan used raw count thresholds only. This contract adds **blast radius** and **flow criticality** so a small number of failures on `payment.place_bet` doesn't get misclassified as LOW.

### Dedup rules (BugReporter checks BEFORE creating)

Two errors are the **same issue** if ALL of:
1. Same `error_type` (exception class name), AND
2. Same `endpoint` (METHOD + path), AND
3. First TBG-owned stack frame is the same file + line (±5 lines to tolerate edits), AND
4. Same `flow` context

If a match is found, BugReporter **updates** the existing issue with a new occurrence count and new sample `trace_id`s rather than creating a duplicate. Comment template:
```markdown
<!-- tbg-bug-update -->
Additional occurrences since {last_update}:
- Count: +{delta}
- New sample trace_ids: {list}
- Blast radius now: {percent}%
```

### Labels

- `Bug` (Backend-Server) or `bug` (Backend-Odds) — existing convention
- `severity:{critical|high|medium|low}` — auto-applied per §A
- `flow:{domain}` — e.g. `flow:bets`, `flow:payments`, `flow:odds`
- `needs-fixer` — default on creation, removed when BugFixer opens a PR

---

## §B — PR format (BugFixer's output)

Every PR BugFixer opens **MUST** include these in the body.

### Required frontmatter

```markdown
<!-- tbg-bug-fix -->
**Fixes**: #{issue_number}
**Root cause category**: `code-bug | config | data | infra | third-party | regression`
**Flow affected**: `{flow_name}` _(from issue)_
**Test-first evidence**: commit `{sha}` adds the failing test BEFORE the fix
**Reproduction**: `/debug-logs trace {trace_id}` (copied from issue)
```

### Required sections

1. **Root cause** — narrative explanation. Why did this happen? Why now? What triggered it? *(not "what the code did" — that's already in the stack trace)*
2. **Why the fix is correct** — the invariant being restored. *(if this is a one-line null-check, explain why the null was possible in the first place)*
3. **Blast radius of the fix** — what other code paths touch the changed code? Any risk of collateral damage?
4. **Test strategy**:
   - **Regression test**: the failing test added in the first commit of this PR.
   - **Integration test** (if the fix touches cross-service code): added / updated.
   - **Verification command**: how to verify locally (`pytest tests/path/to/test.py::test_name`).
5. **Verification in staging**: after merge, the fixer runs `/debug-logs --error-type {error_type} --window 24h` and links the result in a PR comment. If the error is still occurring → reopen the issue.

### Test-first discipline

**Non-negotiable**: the first commit in the PR MUST be a failing test that captures the bug. The fix commit is always second.

```bash
git log --oneline origin/dev..HEAD
# Expected output:
#   <sha2> fix(bets): handle null odds in parlay stake calculation
#   <sha1> test(bets): regression test for BUG-#1234 (null odds → 500)  ← first
```

Why: if the fix commit comes before the test, the test was written *with knowledge of the fix* and may not actually capture the bug. Test-first forces the agent to prove the bug reproduces before fixing.

BugFixer verifies this with `git log` before opening the PR. If violated, BugFixer re-creates the branch from scratch.

### Grouping rules

BugFixer groups issues into **one PR** when ALL of:
1. Same `flow` context, AND
2. Same root cause category, AND
3. Fixes touch overlapping code paths (same module)

Otherwise, **separate PRs**. Wrong grouping is a contract violation — it makes review harder and partial rollback impossible.

### PR labels

- `bug-fix`
- `flow:{domain}` — mirror the issue's flow label
- `severity:{...}` — mirror the issue's severity
- `needs-review` — removed when PR is approved

---

## §C — Post-handoff loop

After the PR is merged and deployed:

1. **BugFixer** waits 1h post-deploy, then queries Grafana: has the error rate for `{error_type}` + `{endpoint}` dropped to zero?
   - **Yes** → close the GitHub issue with a Grafana screenshot. Done.
   - **No** → reopen the issue, add a comment with the new sample trace_ids, and notify BugReporter. BugFixer starts over.

2. **BugReporter** adds the fix to its dedup memory — if the same error pattern reappears within 30 days, BugReporter auto-labels the new issue `suspected-regression` and includes a link to the prior PR.

3. **Daily refactor** (`/daily-refactor` skill, scheduled via nano-claw) scans for `suspected-regression` labels and surfaces them in the weekly report.

---

## §D — What to do when the contract is violated

If BugFixer receives an issue that's missing required frontmatter fields:

1. **Do not fix blindly.** Incomplete context → incomplete fix.
2. Comment on the issue with a machine-readable template listing the missing fields.
3. Notify @BugReporter in `#agentic-dev` so it can backfill the missing data or reclassify the issue.
4. Set the issue to `needs-triage` label.
5. Only start fixing after the contract is satisfied.

If BugReporter detects that a PR doesn't match its issue (wrong fix, wrong flow, etc.):

1. Comment on the PR with the mismatch.
2. Do not close the issue even if the PR merges — reopen if necessary.

---

## §E — Evolution

This contract will drift as the platform grows. Rules for updating it:

- Changes are PRs to `Dev-Agentic/agents/bug-agents-handoff.md`, reviewed like code.
- Breaking changes (removed fields, renamed fields) require a version bump at the top of this file.
- Both agents' CLAUDE.md files must be updated in the same PR as the contract change.
- Post a summary to `#agentic-dev` when the contract changes so running agent sessions are aware.

**Current version**: `v1` (2026-04-09 — initial centralization + structured fields).

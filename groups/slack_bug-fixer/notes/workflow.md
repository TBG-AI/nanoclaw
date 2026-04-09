# BugFixer workflow

Step-by-step procedure for resolving a single issue.

## Phase 1 — Pick an issue

Poll open issues with the `needs-fixer` label:

```bash
gh issue list --repo TBG-AI/Backend-Server --state open --label "needs-fixer" \
  --json number,title,url,body,labels,createdAt
gh issue list --repo TBG-AI/Backend-Odds   --state open --label "needs-fixer" \
  --json number,title,url,body,labels,createdAt
```

**Priority order**:
1. `severity:critical` first, oldest first
2. Then `severity:high`
3. Then medium/low
4. `suspected-regression` bumps priority one level (regressions indicate systemic issues)

Do **not** start a new issue while you have an in-progress fix. One at a time.

## Phase 2 — Validate contract

Read the issue body. Check the `<!-- tbg-bug-report -->` frontmatter contains ALL required fields from handoff §A:

- [ ] error_type
- [ ] service
- [ ] flow + flow_step
- [ ] endpoint
- [ ] first_seen, last_seen
- [ ] occurrences, affected_users
- [ ] severity, blast_radius
- [ ] sample correlation IDs (request_id + trace_id, at least 1 pair)
- [ ] error message
- [ ] top TBG stack frame
- [ ] full stack trace

**If any field missing**:
```bash
gh issue comment <N> --repo <repo> --body "<!-- tbg-bug-fix-triage -->
Cannot start fix — missing required fields per [handoff contract §A](https://github.com/TBG-AI/Dev-Agentic/blob/main/agents/bug-agents-handoff.md):

- [ ] {field1}
- [ ] {field2}

@BugReporter please backfill."
gh issue edit <N> --repo <repo> --add-label "needs-triage" --remove-label "needs-fixer"
```

Stop. Pick the next issue.

## Phase 3 — Reproduce

**Never fix without reproducing first.**

```bash
# Pick the newest sample trace_id from the issue frontmatter
/debug-logs trace <trace_id>
```

This should return the full request trace + logs. Expected: you can see exactly where in the call chain the error occurred.

If reproduction fails (trace not found, too old):
```bash
# Find a fresher sample
/debug-logs error-type "<error_type>" --window 7d --limit 5
```

Pick a fresher `trace_id`, retry.

If still can't reproduce after 2 attempts → this is a rare error. Check if instrumentation is missing. If needed, comment on the issue asking BugReporter for help, and move to the next issue.

## Phase 4 — Locate root cause

Use the stack trace from the issue. Navigate the repo:

```bash
cd /workspace/group/Backend-Server
git checkout dev && git pull origin dev
```

Open the top TBG-owned frame (not stdlib, not vendored libs). Ask yourself:

1. **What assumption did the code make that was violated?**
2. **Why is that assumption wrong now?** (new data, new caller, new upstream behavior?)
3. **Is the bug in the code, or in the data that reached the code?**

**Use flow context**: the issue lists `flow: {name}` — open `specs/flows/flow-registry.json` and the matching PlantUML diagram to understand the business context.

**Check the decorators on the failing function**:
- `@flow_traced(Flow.X)` → service entry point
- `@traced_job(Flow.X)` → background job
- `@traced("name")` → internal span

These tell you whether the bug is at a request boundary (where inputs come from the client) or deeper in the call stack (where inputs come from upstream services).

**Check `specs/flows/` for a diagram**: 166 PlantUML files. Find the one matching your flow. The `@depends-on` comments link to source files — those are the authoritative files for this flow.

## Phase 5 — Write failing regression test FIRST

Before touching the fix, write a test that captures the bug. The test should:
- Exercise the exact code path from the stack trace
- Feed the inputs from the reproduction (or a synthesized equivalent)
- Assert the **correct** behavior (what the code SHOULD do), not the current buggy behavior

**Commit the test first**:
```bash
git checkout -b fix/<issue-number>-<short-description>
# ... add test file ...
git add tests/path/to/test_<feature>.py
git commit -m "test(<scope>): regression test for BUG-#<issue_number>

Captures the bug at {file}:{line} where {short description of the
invariant that was violated}."
```

**Run the test — it MUST fail**:
```bash
pytest tests/path/to/test_<feature>.py::test_regression_bug_<n> -xvs
```

If the test passes (i.e., the bug doesn't reproduce in test form), the test is wrong — rewrite it. A regression test that doesn't fail without the fix is worthless.

## Phase 6 — Implement the fix

Make the minimum change that restores the invariant. Do not:
- Refactor surrounding code
- Improve logging "while I'm here" (that's a separate PR)
- Add comments explaining the bug (the commit message explains it)
- Touch unrelated files

**Commit the fix**:
```bash
git add <files>
git commit -m "fix(<scope>): <short description>

Root cause: {short explanation}
Why it was wrong: {short explanation}
Why this fix is correct: {short explanation}

Fixes #<issue_number>"
```

**Re-run the test — it MUST pass**:
```bash
pytest tests/path/to/test_<feature>.py::test_regression_bug_<n> -xvs
```

## Phase 7 — Run the full test suite

```bash
# Backend-Server
make test  # or equivalent

# Backend-Odds
make test
```

All tests must pass. If anything broke, you introduced a regression — fix it in the same PR. Do NOT disable the broken test.

## Phase 8 — Push and open PR

```bash
git push -u origin fix/<issue-number>-<short-description>

gh pr create --repo TBG-AI/<repo> --base dev \
  --title "fix(<scope>): <description>" \
  --body-file /tmp/pr-body.md \
  --label "bug-fix,flow:<domain>,severity:<sev>,needs-review"
```

PR body MUST follow handoff contract §B. Template:

```markdown
<!-- tbg-bug-fix -->
**Fixes**: #<issue_number>
**Root cause category**: code-bug | config | data | infra | third-party | regression
**Flow affected**: <flow_name>
**Test-first evidence**: commit <sha1> adds the failing test BEFORE the fix
**Reproduction**: `/debug-logs trace <trace_id>`

## Root cause

<narrative>

## Why the fix is correct

<invariant being restored>

## Blast radius of the fix

<what else touches this code>

## Test strategy

- Regression test: `tests/path/to/test_<feature>.py::test_regression_bug_<n>`
- Integration test: <if applicable>
- Verification: `pytest tests/path/to/test_<feature>.py::test_regression_bug_<n>`

## Verification in staging

*(populated after merge + deploy)*
```

## Phase 9 — Wait for CI + review

Poll PR status:
```bash
gh pr view <N> --repo <repo> --json statusCheckRollup,reviews
```

- CI red → investigate, fix, push again
- Review requested changes → address, push again
- Approved + green → wait for human to merge (**you do not merge your own PRs**)

Post to channel when PR is up:
```
*Fix: #<issue>* — PR up
→ TBG-AI/<repo>#<pr>
→ Root cause: <one line>
→ Test-first ✓, CI <status>
```

## Phase 10 — Post-merge verification

After the PR merges, wait for the deploy notification in `#deploys` (or manually check `/cw-logs <service> prod`). Then wait **1 hour** for traffic.

```bash
# Scope to the affected endpoint and window:
/debug-logs error-type "<error_type>" --service <service> --window 1h
```

**Expected**: zero occurrences.

**If zero**:
```bash
gh issue close <N> --repo <repo> --comment "<!-- tbg-bug-fix-verified -->
Verified fixed post-deploy.

- Error: \`<error_type>\` at \`<endpoint>\`
- Window: last 1h
- Occurrences: 0 (was <N>/h before fix)
- Grafana: <url>

Closed by BugFixer."
```

**If not zero**:
```bash
gh issue reopen <N> --repo <repo>
gh issue comment <N> --repo <repo> --body "<!-- tbg-bug-fix-failed -->
Post-deploy verification FAILED.

- Error still occurring: \`<error_type>\`
- New sample trace_ids: <list>
- Occurrences in last 1h: <N>

Restarting fix workflow. Original PR: #<pr>."
gh issue edit <N> --repo <repo> --add-label "needs-fixer"
```

Restart from Phase 3 with the new trace IDs.

## Phase 11 — Self-audit

Append to `notes/fix-history.md`:

```markdown
## 2026-04-09 — Fix #1234 NullOddsError
- Repo: Backend-Server
- PR: #5678
- Root cause category: code-bug
- Flow: bets.place_parlay
- Time to fix: 1h 20min
- Verification: 0 occurrences post-deploy ✓
- Lesson: odds_client.get_parlay_odds() returns None for partially-suspended
  events — all callers must handle this case. Consider making the contract
  explicit via a `ParlayOddsResult` domain type.
```

## Failure modes — full list

See the main CLAUDE.md "Failure modes" table. Rule of thumb: **if you're unsure, stop and ask, don't guess**.

---
name: pr-review
description: Review a PR — validate test script, refine by reading code, leave review comments or fix trivial issues ourselves. Use for "review PR", "look at PR #N", or any PR review request.
user_invocable: true
---

# PR Review

Review any TBG PR against the feature-type checklists in [TBG-DOCS/plans/03-skills/pr-review.md](../../../TBG-DOCS/plans/03-skills/pr-review.md).

## Inputs the skill asks for

1. PR URL or `owner/repo#N` reference
2. Feature type (F-1 SWE / F-2 / F-3 / Daily Refactor) — if not in PR body, ask

## Step 1 — Review the test script first

The test script is the contract. Read it before the impl.

1. Fetch the PR: `gh pr view <N> --repo <owner/repo> --json files,body,title`
2. Identify test files in the diff
3. **Check coverage**: happy path + error cases + edge cases
4. **Check no-mock-DB rule**: integration tests must NOT mock the database. Flag any `@mock.patch` or `MagicMock` on DB sessions. *(Reason: prior incident — mocked tests passed but prod migration failed last quarter.)*
5. **Feature-type-specific checks**:
   - **F-1 SWE**: component tests + integration w/ mock API + E2E stubs + PostHog events wired
   - **F-2**: test written *before* impl (API-first) + real DB in integration tests
   - **F-3**: uses staff-provided mock + live-test marker
6. **Is the test script itself buggy?**
   - If the fix is obvious (typos, wrong assertion, missing import) → **fix it ourselves** in a follow-up commit
   - If not → Step 2

## Step 2 — Refine by reading the code

If the test script alone can't tell you whether the PR is correct, read the impl.

1. Infrastructure → application → domain (bottom-up)
2. Check against the feature-type rules:
   - **F-2 / F-3 with DB changes**: verify [db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md) followed (stale columns w/ comment)
   - **F-2 / F-3 breaking**: verify [stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md) followed (`_legacy.py` duplicate + routing)
   - **F-3**: verify retry + circuit breaker + flow tracing + secret handling
3. Run the tests locally if the PR description doesn't attach results

## Step 2.5 — Observability checks (MANDATORY for F-2, F-3, bug-fix)

Every backend change must maintain the structured-logging + flow-tracing contract. Without these, `/debug-logs`, `@BugReporter`, and `@BugFixer` all degrade silently.

**Hard checks** (fail the review if any are missing):

1. **New HTTP routes MUST be in `ROUTE_TO_FLOW`**
   - File: `src/backend_server/infrastructure/middleware/flow_context.py` (Backend-Server) or equivalent in Backend-Odds
   - Grep the PR diff for new `@router.get/.post/.put/.delete` decorators
   - For each, verify the exact `("METHOD", "/path")` tuple exists in `ROUTE_TO_FLOW`
   - The pre-commit hook (`scripts/check-flow-drift.sh`) enforces this, but review catches it earlier

2. **New service entry points MUST have `@flow_traced`**
   - Grep the PR diff for new methods in `application/services/**/*.py`
   - Each public service method (not private `_helpers`) should be decorated: `@flow_traced(Flow.X)` or `@traced_job(Flow.X)` for background jobs
   - Exception: pure domain logic in `domain/` does NOT need `@flow_traced` (it's deeper than the entry point)

3. **New flows MUST be registered**
   - If the PR adds a new flow name, it MUST appear in:
     - `specs/flows/flow-registry.json` (source of truth)
     - `src/backend_server/core/observability/flows.py` (enum)
   - `./scripts/check-flow-drift.sh` must pass

4. **Structured log calls, not f-strings**
   - Search for `logger.info(f"..."` or `logger.error(f"..."` — these lose structure
   - Correct pattern:
     ```python
     logger.info("Order processed", extra={"context": {"order_id": id, "amount": amt}})
     ```
   - The `context` dict becomes a nested object in Grafana Loki and is queryable
   - Exception: `logger.debug(f"...")` is fine (debug logs aren't shipped in prod)

5. **F-3 external calls MUST include trace propagation**
   - Any new `httpx.AsyncClient` or similar must forward `X-Request-ID` and `X-Flow` headers to downstream services
   - Reference impl: `src/backend_server/infrastructure/microservices/odds_client.py`

6. **Bug-fix PRs MUST include the `Fixes #N` frontmatter per handoff contract §B**
   - If the PR title contains "fix:" or "Fix:", it should satisfy [`agents/bug-agents-handoff.md §B`](../../../agents/bug-agents-handoff.md)
   - Check: root cause section, test-first evidence (`git log` shows test commit BEFORE fix commit), reproduction command

**Reproducibility check** (for bug-fix PRs):
- Run the reproduction command from the issue: `/debug-logs trace <trace_id>`
- Confirm the trace matches what the PR claims it's fixing
- If the trace shows a different code path than the fix, the PR is fixing the wrong thing

## Step 3 — Decision

Three outcomes:

1. **Approve** — all checks pass. `gh pr review <N> --approve --body "LGTM"`
2. **Request changes** — leave specific comments tied to files/lines, reference the rule docs by name
3. **Fix it ourselves** — for small issues, push a follow-up commit directly

Don't bottleneck on the author for trivial changes.

## Per-feature-type checklists

### F-1 SWE
- [ ] Test script: component + integration + E2E stubs
- [ ] PostHog events wired
- [ ] Feature flag registered
- [ ] Mock API matches F-2 contract (if parallel F-2 task exists)
- [ ] Theme tokens used (no hardcoded colors/spacing)

### F-2
- [ ] Test written before impl (check git history — first commit should be the failing test)
- [ ] Integration tests hit real DB (no `@mock.patch` on DB sessions)
- [ ] DDD layers respected (infra depends on app depends on domain, not reverse)
- [ ] DB migration follows stale-column rules (if any)
- [ ] Breaking changes follow stale-code rules (if any)
- [ ] `AI_DOCS/api-impl/<feature>.md` exists and matches impl
- [ ] **New routes added to `ROUTE_TO_FLOW`** (`infrastructure/middleware/flow_context.py`)
- [ ] **New service methods have `@flow_traced(Flow.X)`**
- [ ] **Structured log calls** use `extra={"context": {...}}` — not f-strings
- [ ] Flow enum + registry updated if a new flow is introduced

### F-3
- [ ] Staff mock + border docs linked
- [ ] Retry + circuit breaker present
- [ ] Flow added to `specs/flows/flow-registry.json` (source of truth)
- [ ] Flow enum in `core/observability/flows.py` updated
- [ ] Secrets via env config (no hardcoded keys)
- [ ] Rate limit guard present
- [ ] Failure modes documented
- [ ] **`X-Request-ID` + `X-Flow` headers forwarded to external service** (trace propagation)
- [ ] **External call has structured error logging with `extra={"context": {...}}`**

### Bug-fix (from @BugFixer or manual fix)
- [ ] Frontmatter follows [handoff contract §B](../../../agents/bug-agents-handoff.md) — `Fixes #N`, root cause category, flow, test-first evidence, reproduction command
- [ ] First commit is the failing regression test; fix commit is second (verify with `git log --oneline origin/dev..HEAD`)
- [ ] Regression test references the issue number in its docstring or commit message
- [ ] Reproduction command (`/debug-logs trace <trace_id>`) matches the code path being fixed
- [ ] Root cause narrative explains *why* the invariant was violated, not just *what* the code did
- [ ] Blast-radius of the fix is documented

### All types
- [ ] No `.env` / credentials committed
- [ ] No `git add -A` sweeping in secrets
- [ ] CI passing (or explanation if not)

## Cross-references

- Plan spec: [TBG-DOCS/plans/03-skills/pr-review.md](../../../TBG-DOCS/plans/03-skills/pr-review.md)
- Feature types: [TBG-DOCS/plans/03-skills/feature-impl-types.md](../../../TBG-DOCS/plans/03-skills/feature-impl-types.md)
- DB rules: [TBG-DOCS/plans/03-skills/db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md)
- Stale code: [TBG-DOCS/plans/03-skills/stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md)
- API impl doc: [TBG-DOCS/plans/03-skills/api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md)

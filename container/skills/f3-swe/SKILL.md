---
name: f3-swe
description: F-3 SWE role — backend feature with external service. Same as F-2 plus staff-provided mock/border, retry, circuit break, rate limits, and flow registry wiring. Use when user says "F-3" or mentions integration with an external service (Kalshi, Stripe, PayPal, PostHog, Grafana, FanDuel, etc.).
user_invocable: true
---

# F-3 SWE — Backend, With External Service

You are the **F-3 SWE** role. Same base flow as [`f2-swe`](../f2-swe/SKILL.md) — backend feature, API-first, DDD layers, real-DB integration tests — **but** the feature integrates with a **third-party service** (Kalshi, Stripe, PayPal, PostHog, Grafana, FanDuel, WhatsApp, Twilio, etc.). That changes everything about the border, the error handling, and what staff must provide up front.

Plan spec: [TBG-DOCS/plans/03-skills/f3-swe.md](../../../TBG-DOCS/plans/03-skills/f3-swe.md).

## ⛔ Prerequisite: staff must provide the inputs before impl starts

**Refuse to start** if any of these are missing. Ping the user to get them from a senior/staff engineer:

1. **Mock fixture** — what the external service's response looks like. JSON file, Python fake class, or recorded HTTP cassette. Goes under `tests/fixtures/<service>/*.json` or similar.
2. **Service border** — a diagram or a clear written description of:
   - What lives **inside** our code: HTTP client, retry logic, circuit breaker, mapper, domain translator
   - What lives **outside**: the external API itself
   - Where the **seam** is: the interface the application service talks to (usually a port/protocol)
3. **Failure modes** — what we do when the external service is:
   - **Down** (connection refused / timeout)
   - **Slow** (latency spike → should circuit-break)
   - **4xx** (our fault → log, surface to caller)
   - **5xx** (their fault → retry with backoff, then 502)
4. **Rate limits + quotas** — req/s, daily cap, cost per call, what happens at the limit
5. **Secrets** — which env var names, which S3 env config key. Never committed. **Confirm with staff which secret store**.

Print a block like this back to the user on start:

```
F-3 requires staff to provide:
  [ ] Mock fixture path
  [ ] Service border (what's inside vs outside, where the seam is)
  [ ] Failure mode expectations
  [ ] Rate limit / quota
  [ ] Secret env var names + S3 env config location

Do you have all of these? (y/n)
```

If `n`, stop and wait. Do not write any code.

## Inputs the skill asks for (after prereqs are satisfied)

1. **Target repo** — `Backend-Server` or `Backend-Odds` (or `tbg-streaming`)
2. **External service name** — e.g., `kalshi`, `stripe`, `paypal`
3. **Feature name** — kebab-case
4. **Endpoints** — our endpoints that call into this integration
5. **Mock fixture path** (from staff)
6. **Service border doc/link** (from staff)
7. **Failure modes** (from staff)
8. **Rate limit + quota** (from staff)
9. **Secret env var names** (from staff)
10. **Breaking?** / **DB migration?** — same as F-2

## Flow (F-2 steps 1-5 + F-3 additions)

### Step 1 — API impl doc + mock + border

1. Create `<repo>/AI_DOCS/api-impl/<feature>.md` following [api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md). **F-3 requires extra sections** on top of the F-2 baseline:
   - **Service border** — inside/outside/seam, with the exact path of the HTTP client file
   - **Secrets** table — env var, source (S3 env config), notes
   - **Rate limits** — max req/s, daily cap, cost per call
   - **Failure modes** — table of mode → our behavior
2. Drop the **staff-provided mock fixture** into `tests/fixtures/<service>/` and reference it from the API impl doc
3. Link to the staff failure-mode notes (Notion page, PR comment, Slack thread, etc.)
4. If F-1 SWE created a Frontend mock for the TBG-facing endpoint, link it too

### Step 2 — API-first: test → impl → end

Same as F-2 but with these differences:

- **Integration tests use the staff mock**, not the real external service. CI never calls the live external API.
- Optional `@pytest.mark.live` marker for manual verification before deploy — runs against the real service with real credentials. Off by default.
- **Integration test still uses the real DB** — do NOT mock the database (project memory: mocked tests passed but a prod migration failed last quarter; integration tests must hit real DB). Use `get_test_session()` + `load_test_env()` from `tests/<domain>/utils.py` just like F-2.
- The implementation talks to the **service-border interface** (port/protocol), not directly to `httpx`. This is what makes unit tests trivial and lets you swap in a fake.

### Step 3 — Define the full test script

1. **Unit tests for the HTTP client**, using a fake backend for every failure mode from staff (down, slow, 4xx, 5xx). Assert retry count + circuit breaker trip conditions.
2. **Unit tests for the application service** with a mocked port (not mocked DB).
3. **Integration tests** (real DB + mock external service) for the happy path + the most impactful failure modes.
4. **Live tests** (gated) for the single happy path against the real service. Skip in CI.

### Step 4 — Implementation (additions vs F-2)

Follow the **DDD layering** from F-2 (routes → services → domain + repos + adapters). F-3 adds specific pieces:

1. **HTTP client** — `src/backend_server/infrastructure/microservices/<service>_client.py` (Backend-Server) or `src/backend_odds/infrastructure/<category>/<service>_client.py` (Backend-Odds). For third-party adapters (Expo, PayPal, Kalshi, etc.), prefer `src/backend_server/infrastructure/third_party/<service>/` per the DDD overview.
2. **Retry + circuit breaker — reference the canonical pattern**: `Backend-Server/src/backend_server/infrastructure/microservices/odds_client.py`. Mirror its structure:
   - Constructor takes the base URL (and optional timeout override)
   - `async with httpx.AsyncClient(timeout=...)` per call
   - **Typed exception translation**: catch `httpx.HTTPStatusError` / `httpx.ReadError` / `httpx.ConnectError` / generic `Exception` and raise domain-level errors from `application/exceptions.py` (e.g., `OddsMicroserviceRequestError`, `SamePlayerAndActionError`). Do **not** let raw `httpx` errors escape the adapter.
   - Status-code-specific branches (400 → input error, 5xx → retry error)
   - Structured logging at every branch
   - Add explicit retry-with-backoff (e.g., via `tenacity`) and a circuit breaker (e.g., `pybreaker` or a counter-based trip) on top of the odds_client pattern when the external service is flaky and staff requested it.
3. **Fake/mock backend** — the client should be injectable: production uses the real `httpx` backend, tests use a fake. Look at `Backend-Server/src/backend_server/infrastructure/microservices/mock_odds_client.py` for the pattern.
4. **Flow tracing** — add the flow to the registry and wire `@flow_traced`. From `TBG-DOCS/CLAUDE.md`:
   - Add entry to `TBG-DOCS/flows/flow-registry.json`: `{ "name": "DOMAIN_ACTION", "value": "domain.action", "description": "..." }`
   - Add enum value to `Backend-Server/src/backend_server/core/observability/flows.py` (or Backend-Odds equivalent: `src/backend_odds/core/observability/flows.py`)
   - Add route mapping in `infrastructure/middleware/flow_context.py` (Backend-Server) or `infrastructure/web/middleware/request_context.py` (Backend-Odds) — `ROUTE_TO_FLOW` dict
   - Decorate the service method: `@flow_traced(Flow.DOMAIN_ACTION)`
   - Run `./scripts/check-flow-drift.sh` from `TBG-DOCS/` to verify everything is in sync
5. **Secrets** — never commit.
   - Env var names go in the API impl doc's **Secrets** table
   - Values land in the **S3 env config** — confirm the exact path with staff, then update locally via the env management script (`Backend-Server/scripts/env_management/`)
   - Confirm `.env` / `.env.docker` / `.env.prod` / `.env.stage` **do not** contain the new secret before committing
6. **Rate limit guard** — if staff specified a quota:
   - Add a counter (Redis or in-process)
   - Alert when crossing 80% of daily cap
   - Hard-fail at 100% with a typed exception, not a raw HTTP error
7. **PostHog events** — if the integration emits user-facing events, register them in `TBG-DOCS/event-registry.json` and Frontend `packages/shared/src/posthog/constants/events.ts` per `TBG-DOCS/CLAUDE.md` "How to: Add a new PostHog event".
8. **DB migration** (if any) — **read [db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md) first**. Alembic locations: `Backend-Server/alembic/` (main) or Backend-Odds' `alembic/`, `alembic_postgres/`, `alembic_ext_odds/`, `alembic_remote_postgres/` — pick the right one.
9. **Stale code** (breaking changes only) — **read [stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md) first**. Duplicate the file, `_legacy.py` suffix, route on `request.state.app_version`.

### Step 5 — PR body (additions vs F-2)

```markdown
**Feature type**: F-3

**External service**: <name>
**Breaking**: yes / no
**DB migration**: yes / no
**API.Impl.Md**: `AI_DOCS/api-impl/<feature>.md`
**Mock fixture**: `tests/fixtures/<service>/<file>`
**Service border**: see `AI_DOCS/api-impl/<feature>.md#service-border`
**Failure modes**: documented in API impl doc
**Rate limit**: <req/s>, daily cap <N>, cost per call <$>
**Secret env vars added**: <LIST> (source: S3 env config)
**Flow added to registry**: yes / no — `<flow.name>`

## Summary
<1-3 bullets>

## Test results

```
tests/<domain>/unit/test_<service>_client.py::test_down_mode             PASSED
tests/<domain>/unit/test_<service>_client.py::test_slow_mode_trips_cb    PASSED
tests/<domain>/unit/test_<service>_client.py::test_4xx_surfaces          PASSED
tests/<domain>/unit/test_<service>_client.py::test_5xx_retries           PASSED
tests/<domain>/unit/test_<feature>_service.py::test_service_logic        PASSED
tests/<domain>/integration/test_<feature>.py::test_happy_path            PASSED
tests/<domain>/integration/test_<feature>.py::test_upstream_down         PASSED

Coverage: <N>%
```

## Checklist
- [ ] Staff-provided mock + border linked in API impl doc
- [ ] Retry + circuit breaker present (pattern: `infrastructure/microservices/odds_client.py`)
- [ ] Fake backend for unit tests
- [ ] Flow added to `specs/flows/flow-registry.json` + enum + route map + `@flow_traced` + drift check passes
- [ ] Secrets via S3 env config (no hardcoded keys, no secrets in `.env*` committed)
- [ ] Rate limit guard present
- [ ] Failure modes documented in API impl doc
- [ ] Integration tests use real DB (no mocks) + mock external service
- [ ] `@pytest.mark.live` test exists and is skipped in CI
- [ ] DB migration follows stale-column rules (N/A if no migration)
- [ ] Breaking changes follow stale-file rules (N/A if not breaking)
- [ ] **Instrumentation + external-service observability**: see checklist below

## Instrumentation checklist (MANDATORY — F-3 extends F-2's checklist)

F-3 features hit third-party services — which means more ways for bugs to hide and more reasons to instrument carefully. Every F-3 PR MUST satisfy everything in [`f2-swe` instrumentation checklist](../f2-swe/SKILL.md#instrumentation-checklist-mandatory), PLUS:

- [ ] **Trace propagation across the boundary**: `X-Request-ID` and `X-Flow` headers are forwarded to the external service (if it accepts them). At minimum, the outgoing HTTP client includes them as request headers so you can correlate your logs with the third-party's logs if they provide correlation.
- [ ] **Circuit breaker state is logged**: every open/half-open/closed transition logs with `extra={"context": {"cb_state": "...", "service": "..."}}`. Without this, `/debug-logs` can't tell you whether a failure was real or just the CB tripped.
- [ ] **Retry attempts are logged**: each retry attempt logs with `extra={"context": {"attempt": N, "backoff_ms": X}}` and includes the error type from the previous attempt. Don't log at `ERROR` for retries that eventually succeed — use `WARNING`.
- [ ] **Rate limit hits are logged distinctly**: a rate-limit response (429 or equivalent) logs at `WARNING` with a dedicated error type (e.g., `RateLimitExceeded`) so BugReporter can distinguish "we got throttled" from "their service is broken".
- [ ] **External service latency histogram**: metrics are emitted for external call duration, labeled by service name. Pattern: `http_client_duration_seconds{service="kalshi", endpoint="/markets"}`.
- [ ] **Fixture-based tests verify error paths**: the staff-provided mock fixture includes error responses (5xx, 4xx, timeouts), and unit tests exercise each.
- [ ] **`@pytest.mark.live` test**: a test that hits the real external service, skipped in CI via `pytest -m "not live"`. Run manually before merging to verify the integration actually works.

### Why each rule exists

- **Trace propagation** — lets you correlate a failed request to what the third-party saw. Critical when the other team says "we don't see the request on our end."
- **Circuit breaker logging** — without it, a CB-tripped failure looks identical to a real upstream failure, and BugReporter files a spurious issue.
- **Distinct retry/rate-limit logging** — prevents BugReporter from classifying transient retries as persistent errors.
- **Latency histogram** — the first thing you check when a third-party integration gets slow. Without it, you can't tell if Kalshi is slow or your code is slow.
- **Live test** — staging mocks drift from reality. A `@pytest.mark.live` test catches contract changes before they become 2am incidents.

See [`.claude/skills/pr-review/SKILL.md` Step 2.5](../pr-review/SKILL.md) for the PR-review side of these checks.

**Linked F-1 SWE task**: #<number> (if any)
```

Then hand off:

1. **To `pr-review`** — for review
2. **To `deploy`** — once approved and merged. The deploy skill needs to know the new secrets are in S3 env config **before** shipping.

Do NOT self-merge or self-deploy.

## Handoff

- On merge, move `AI_DOCS/api-impl/<feature>.md` → `AI_DOCS/reference/api-impl/<feature>.md` (doc lifecycle)
- Fire the `deploy` skill
- If this was the first F-3 for this external service, remind staff to add the service to the monitoring dashboard (latency, error rate, circuit-breaker state, quota consumption)

## Cross-references

- Plan spec: [TBG-DOCS/plans/03-skills/f3-swe.md](../../../TBG-DOCS/plans/03-skills/f3-swe.md)
- Sibling base flow: [f2-swe](../f2-swe/SKILL.md)
- Feature types: [TBG-DOCS/plans/03-skills/feature-impl-types.md](../../../TBG-DOCS/plans/03-skills/feature-impl-types.md)
- API impl doc: [TBG-DOCS/plans/03-skills/api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md)
- DB rules: [TBG-DOCS/plans/03-skills/db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md)
- Stale code: [TBG-DOCS/plans/03-skills/stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md)
- **Retry + circuit breaker reference**: `Backend-Server/src/backend_server/infrastructure/microservices/odds_client.py`
- **Fake client reference**: `Backend-Server/src/backend_server/infrastructure/microservices/mock_odds_client.py`
- Flow / event registry how-to: `TBG-DOCS/CLAUDE.md`
- DDD layering: `Backend-Server/docs/dev/ddd/overview.md`
- Error handling: `Backend-Server/docs/dev/error-handling/overview.md`
- Review: [pr-review](../pr-review/SKILL.md)
- Deploy: `deploy` skill

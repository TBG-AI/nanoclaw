---
name: f2-swe
description: F-2 SWE role — implement a backend feature with no external service. API-first (test → impl → end). Use when user says "F-2", "implement backend API", "backend feature", or the task is a TBG-owned backend change (Backend-Server, Backend-Odds) with no third-party integration.
user_invocable: true
---

# F-2 SWE — Backend, No External Service

You are the **F-2 SWE** role for TBG. The feature is backend-only and uses **only** TBG-owned services (Backend-Server ↔ Backend-Odds, own DB, own Redis). **No third-party API.** If the feature touches a third-party service (Kalshi, Stripe, PayPal, PostHog, Grafana, etc.), stop and hand off to `f3-swe` instead.

**Core principle: API-first. test → impl → end.** Write the test *before* the implementation.

Plan spec: [TBG-DOCS/plans/03-skills/f2-swe.md](../../../TBG-DOCS/plans/03-skills/f2-swe.md).

## Inputs the skill asks for

1. **Target repo** — `Backend-Server` or `Backend-Odds` (or `tbg-streaming`)
2. **Feature name** — kebab-case (e.g., `bet-backing-share`, `parlay-odds-v2`)
3. **Endpoint(s)** — method + path + auth + purpose
4. **Request/response schema** — or a link to the F-1 SWE mock that defined it
5. **Breaking?** — if yes, the old build version cutover
6. **DB migration?** — if yes, which tables

If the feature was triggered by an F-1 SWE mock, grab the mock path from the Frontend repo and pin it in the API impl doc.

## Step 1 — API impl doc + connect mock

1. Create `<repo>/AI_DOCS/api-impl/<feature>.md` following the [api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md) standard. Required sections: Endpoint(s), Request schema, Response schema, Error responses, Domain mapping, Test coverage, Frontend contract link, DB migration, Stale code, Deployment.
2. If the Frontend F-1 SWE created a mock for this endpoint, note the mock path under **Frontend contract link** (usually `Frontend/packages/shared/src/mocks/<feature>.ts`).
3. Confirm request/response schema matches what Frontend expects. If not, **stop and sync with Frontend** before writing a single line of backend code.
4. Set doc status to `draft`.

## Step 2 — API-first: test → impl → end

This is the **core principle** of F-2. In order:

### 2a. Write the integration test first (the contract)

- Lives in `<repo>/tests/<domain>/integration/test_<feature>.py`
- Uses the **real database** via `get_test_session()` from `tests/<domain>/utils.py` — **do NOT mock the DB** (project memory: mocked tests passed but a prod migration failed last quarter; integration tests must hit real DB)
- Load env with `load_test_env()` before importing backend modules
- Covers at minimum:
  - Happy path (full request → response)
  - At least 2 error cases (invalid input, auth failure, not-found, race condition, etc.)
- Run via `./scripts/env_management/runners/run_with_env.sh local python -m tests.<domain>.integration.test_<feature>` (Backend-Server) or the repo's equivalent test runner

This test *will fail*. That's the point — it is the contract for the impl.

### 2b. Write the implementation

Follow the DDD layering from `Backend-Server/docs/dev/ddd/overview.md`:

```
infrastructure/api/rest/      ← Routes (thin FastAPI controllers, no business logic)
application/services/         ← Services (business logic, orchestration)
application/ports/            ← Repo interfaces / protocols
domain/                       ← Entities, value objects, schemas (pure Python)
infrastructure/repositories/  ← All DB access (SQLAlchemy ORM, via UoW)
```

Concrete paths in Backend-Server:
- Route: `src/backend_server/infrastructure/api/rest/<feature>_routes.py`
- Service: `src/backend_server/application/services/<domain>/<feature>_service.py`
- Repo: `src/backend_server/infrastructure/repositories/<domain>/<feature>_repository.py`, wired into `infrastructure/database/unit_of_work.py`
- Domain entity: `src/backend_server/domain/<domain>/<entity>.py`
- Request/response schemas: `src/backend_server/application/schemas/requests/` and `application/schemas/responses/` (use Pydantic + `response_model=` on routes per `Backend-Server/CLAUDE.md`)

Concrete paths in Backend-Odds:
- Route/API: `src/backend_odds/infrastructure/api/` and `infrastructure/web/`
- Service: `src/backend_odds/application/service/`
- Interface/ports: `src/backend_odds/application/interface/` or `application/ports.py`
- Repo: `src/backend_odds/infrastructure/repositories/`
- Domain: `src/backend_odds/core/` (entities, schemas, prediction models)

Rules (from `.claude/rules/architecture.md`):
- Services **never** import SQLAlchemy models or write raw SQL
- All DB access goes through repositories (via UoW in Backend-Server)
- Routes are thin: parse → call service → return response
- Domain layer is pure Python — no infrastructure imports

### 2c. Verify end-to-end

- Run the integration test from 2a — it must pass
- Boot the backend locally (e.g., `python -m backend_server.app`) and hit the endpoint with `curl` or `httpx` once, confirming the request/response matches the API impl doc

## Step 3 — Define the full test script

Beyond the integration test from Step 2:

1. **Unit tests — domain** (`tests/<domain>/unit/test_<entity>.py`)
   - Pure functions on entities, value objects, policies
   - No DB, no I/O
2. **Unit tests — application service** (`tests/<domain>/unit/test_<feature>_service.py`)
   - Mock the **repo interface** (not the DB) and any injected collaborators
   - Follow the existing pattern in `tests/bets/unit/test_game_multipliers.py` (create a `MagicMock` for the repo/client and assert calls)
3. **Edge cases**: null, empty, oversized payloads, concurrent requests (race conditions), auth missing, expired token
4. **Coverage target**: ≥80% for new code

Update the **Test coverage** checklist in the API impl doc.

## Step 4 — Fill in the implementation

By Step 2 you already have a working impl. Step 4 is where you:

1. **Fill in any TODO spots** left from the quick path in Step 2b
2. **Logging + flow tracing** — add `@flow_traced(Flow.<NAME>)` to the service method (per `TBG-DOCS/CLAUDE.md`). If the flow doesn't exist yet, this is an F-2 — you usually reuse an existing flow rather than add a new one. If you *do* need a new flow, follow the "How to: Add a new business flow" steps in `TBG-DOCS/CLAUDE.md`:
   - Add to `TBG-DOCS/flows/flow-registry.json`
   - Add enum value to `src/backend_server/core/observability/flows.py` (or Backend-Odds equivalent)
   - Add route mapping in `infrastructure/middleware/flow_context.py` `ROUTE_TO_FLOW`
   - Run `./scripts/check-flow-drift.sh` to verify
3. **Metrics** — PostHog events via `trackEvent`-style patterns, or Prometheus metrics, matching what already exists in the target domain. If a new PostHog event is needed, follow "How to: Add a new PostHog event" in `TBG-DOCS/CLAUDE.md` and update `TBG-DOCS/event-registry.json`.
4. **DB migration** (if any)
   - **Read [db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md) first.** Non-negotiable.
   - Alembic lives at `Backend-Server/alembic/` (config `alembic.ini`) or `Backend-Odds/alembic/`, `alembic_postgres/`, `alembic_ext_odds/`, `alembic_remote_postgres/`. Pick the right one for the DB you're touching.
   - Key rules: additive-only, columns nullable or with default, **never drop + rename in one PR**, rename = add-new + copy + leave old as stale + drop in follow-up, mark stale columns with `# TODO: Stale column; build version = "X.Y.Z"` comment.
5. **Stale code** (breaking changes only)
   - **Read [stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md) first.**
   - Duplicate the file: `<feature>_service.py` (new) + `<feature>_service_legacy.py` (old), top-of-file header `# Stale Code: Build version = "X.Y.Z"`
   - Route at the application layer based on `request.state.app_version` / `request.state.app_type`
   - Never edit shared code in place for a breaking change

Promote the API impl doc status to `in review` once Step 4 is complete.

## Step 5 — PR with test results

Run the full test suite and capture output. PR body template:

```markdown
**Feature type**: F-2

**Breaking**: yes / no
**DB migration**: yes / no
**API.Impl.Md**: `AI_DOCS/api-impl/<feature>.md`

## Summary
<1-3 bullets on what the feature does>

## Test results

```
tests/<domain>/integration/test_<feature>.py::test_happy_path       PASSED
tests/<domain>/integration/test_<feature>.py::test_invalid_input    PASSED
tests/<domain>/integration/test_<feature>.py::test_concurrent       PASSED
tests/<domain>/unit/test_<feature>_service.py::test_service_logic   PASSED
tests/<domain>/unit/test_<entity>.py::test_entity_invariant         PASSED

Coverage: <N>%
```

## Checklist
- [ ] Test written before impl (API-first) — verifiable from git history
- [ ] Integration tests hit real DB (no mocks)
- [ ] DDD layers respected (routes thin, services don't import SQLAlchemy, repos handle all DB)
- [ ] `AI_DOCS/api-impl/<feature>.md` matches impl
- [ ] DB migration follows stale-column rules (N/A if no migration)
- [ ] Breaking changes follow stale-file rules (N/A if not breaking)
- [ ] **Instrumentation**: see checklist below

## Instrumentation checklist (MANDATORY)

Without this, `/debug-logs`, `@BugReporter`, and `@BugFixer` degrade. Every F-2 PR MUST satisfy:

- [ ] **New route → `ROUTE_TO_FLOW`**: every new `@router.get/.post/...` has a matching entry in `src/backend_server/infrastructure/middleware/flow_context.py`. Format: `("POST", "/your/endpoint"): "domain.action"`
- [ ] **Service entry point → `@flow_traced`**: each new public service method in `application/services/**/*.py` is decorated with `@flow_traced(Flow.X)`. Background jobs use `@traced_job(Flow.X)` instead.
- [ ] **Flow registered**: if a new flow name is introduced, it exists in both `specs/flows/flow-registry.json` AND `src/backend_server/core/observability/flows.py`. Run `./scripts/check-flow-drift.sh` — it must pass.
- [ ] **Structured log calls**: use `logger.info("msg", extra={"context": {...}})`, never f-strings. Exception: `logger.debug(f"...")` is fine (debug logs aren't shipped in prod).
- [ ] **Exceptions registered**: new domain exceptions defined in `application/exceptions.py` AND registered in `infrastructure/api/rest/constants.py` (`ALL_ERROR_MAPPING`). Otherwise the API returns generic 500 instead of the right status.
- [ ] **Pre-commit hook clean**: `./scripts/check-flow-drift.sh` exits 0. The pre-commit hook runs this automatically; don't `--no-verify`.

### Why each rule exists

- **ROUTE_TO_FLOW mapping** — without it, `@flow_traced` can't resolve the flow name, and logs lose the `flow` field. `@BugReporter` can't group errors by flow, severity classification fails.
- **`@flow_traced` decorator** — sets the `flow_ctx` ContextVar, creates an OTEL span. Without it, logs are orphaned and traces are incomplete.
- **Structured log calls with `extra={"context": {...}}`** — f-strings lose the field structure; `context` becomes a nested object in Grafana Loki and is queryable by Bug agents.
- **Exception mapping** — if `NullOddsError` isn't in `ALL_ERROR_MAPPING`, the API returns 500 with a generic message, which confuses BugReporter's routing.

See [`.claude/skills/pr-review/SKILL.md` Step 2.5](../pr-review/SKILL.md) for the PR-review side of these checks.

**Linked F-1 SWE task**: #<number> (if triggered by a frontend feature)
```

Then hand off:

1. **To `pr-review`** — for review of the PR
2. **To `deploy`** — once approved and merged

Do NOT self-merge or self-deploy.

## Handoff

- On merge, move `AI_DOCS/api-impl/<feature>.md` to `AI_DOCS/reference/api-impl/<feature>.md` (doc lifecycle rule from `Backend-Server/CLAUDE.md`)
- Fire the `deploy` skill to ship the change

## Cross-references

- Plan spec: [TBG-DOCS/plans/03-skills/f2-swe.md](../../../TBG-DOCS/plans/03-skills/f2-swe.md)
- Feature types: [TBG-DOCS/plans/03-skills/feature-impl-types.md](../../../TBG-DOCS/plans/03-skills/feature-impl-types.md)
- API impl doc: [TBG-DOCS/plans/03-skills/api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md)
- DB rules: [TBG-DOCS/plans/03-skills/db-migration-rules.md](../../../TBG-DOCS/plans/03-skills/db-migration-rules.md)
- Stale code: [TBG-DOCS/plans/03-skills/stale-code-rules.md](../../../TBG-DOCS/plans/03-skills/stale-code-rules.md)
- DDD layering: `Backend-Server/docs/dev/ddd/overview.md`
- Flow/event registry: `TBG-DOCS/CLAUDE.md` (add-flow / add-event how-to)
- Sibling: [f3-swe](../f3-swe/SKILL.md) — backend feature **with** external service
- Review: [pr-review](../pr-review/SKILL.md)
- Deploy: `deploy` skill

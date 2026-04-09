# Code location reference

Quick reference for where things live in Backend-Server and Backend-Odds. Extend as you learn.

## Backend-Server — key paths

### DDD layering
The project follows Domain-Driven Design with hexagonal architecture.

- `src/backend_server/domain/` — pure domain models, no framework deps
- `src/backend_server/application/` — use cases, service objects, schemas
- `src/backend_server/infrastructure/` — adapters (REST, DB, external APIs)
- `src/backend_server/core/` — cross-cutting (observability, config, utilities)

**Rule**: infrastructure depends on application, application depends on domain. Never the other way around. If your fix imports from infrastructure into application, you're probably violating layering — check `docs/dev/ddd/` first.

### Observability
| Concern | File |
|---|---|
| JSON log formatter | `src/backend_server/logging_formatter.py` (**top-level, NOT under middleware/**) |
| ContextVars | `src/backend_server/core/observability/context.py` |
| `@flow_traced`, `@traced_job`, `@traced` decorators | `src/backend_server/core/observability/tracing.py` |
| Flow enum | `src/backend_server/core/observability/flows.py` |
| Route → flow mapping | `src/backend_server/infrastructure/middleware/flow_context.py` (207+ routes) |
| Request ID middleware | `src/backend_server/infrastructure/middleware/request_id.py` |
| Metrics middleware | `src/backend_server/infrastructure/middleware/metrics_middleware.py` |
| Hierarchical log levels | `src/backend_server/config/core/logging.py` |

### Error handling
| Concern | File |
|---|---|
| Exception handlers | `src/backend_server/app.py` (lines 216-407) |
| Error mapping (`ALL_ERROR_MAPPING`) | `src/backend_server/infrastructure/api/rest/constants.py` |
| Domain exceptions | `src/backend_server/application/exceptions.py` |

When a new exception type is needed: define in `application/exceptions.py`, register in `infrastructure/api/rest/constants.py`. See `docs/dev/error-handling/` for the full pattern.

### Hot-path services (common bug locations)
| Area | File |
|---|---|
| User bet service | `src/backend_server/application/services/bets/user_bet_service.py` |
| Bet routes | `src/backend_server/infrastructure/api/rest/bet_routes.py` |
| Odds microservice client | `src/backend_server/infrastructure/microservices/odds_client.py` |
| Payment services | `src/backend_server/application/services/payments/` |
| Auth routes | `src/backend_server/infrastructure/api/rest/auth_routes.py` |

### Response schemas
Every endpoint should use a Pydantic response schema:
- Request schemas: `src/backend_server/application/schemas/requests/`
- Response schemas: `src/backend_server/application/schemas/responses/`
- Example: `response_model=TeamFull` in the route decorator

### Flow registry
- Source of truth: `specs/flows/flow-registry.json` (submodule from TBG-AI/docs)
- Enum: `src/backend_server/core/observability/flows.py`
- Route mapping: `infrastructure/middleware/flow_context.py` → `ROUTE_TO_FLOW` dict
- Drift check: `scripts/check-flow-drift.sh` (runs as pre-commit hook)

**If your fix adds a new route**: you MUST update `ROUTE_TO_FLOW` and the flow enum, otherwise drift check fails in CI.

### Diagrams
- 166 PlantUML files in `specs/flows/` (from TBG-AI/docs submodule)
- Structure: `C4-system-context.puml`, `L0-*`, `L1-*`, `L2-*`, `L3-*`
- `@depends-on` comments link diagrams to source files — these are authoritative for understanding a flow

## Backend-Odds — key paths

Mirrors Backend-Server where possible:

| Concern | File |
|---|---|
| ContextVars | `src/backend_odds/core/observability/context.py` |
| Decorators | `src/backend_odds/core/observability/tracing.py` |
| Logger utils | `src/backend_odds/core/utils/logger_utils.py` |
| Request context middleware | `src/backend_odds/infrastructure/web/middleware/request_context.py` |
| FastAPI app | `src/backend_odds/infrastructure/web/app.py` |
| WebSocket handler | `src/backend_odds/infrastructure/api/websocket/handler.py` |

External integrations (Kalshi, FanDuel, etc.) live under `src/backend_odds/infrastructure/external/<service>/`.

## Cross-service protocol

- Backend-Server → Backend-Odds: HTTP calls from `infrastructure/microservices/odds_client.py`
- Correlation headers: `X-Request-ID` (UUID), `X-Flow` (flow name)
- Backend-Odds reads these headers in `infrastructure/web/middleware/request_context.py` and sets its ContextVars so logs are correlatable across services

**Fixing cross-service bugs**: check *both* logs using `/debug-logs request <request_id>` — the same request ID appears in both services' logs.

## Testing conventions

### Backend-Server
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/` (hit real DB via testcontainers)
- **Rule**: integration tests MUST NOT mock the database (`@mock.patch` on DB sessions). Reason: prior incident where mocked tests passed but prod migration failed.
- Run: `pytest tests/path -xvs` for a single test, `make test` for the suite

### Backend-Odds
- Same layout
- External services (Kalshi, FanDuel, etc.) use staff-provided fixture files under `tests/fixtures/<service>/*.json`
- Never make real external API calls in tests

## Common pitfalls

1. **Forgetting `@flow_traced`** on a new service method → flow context is lost, logs are harder to correlate. PR review will catch this.
2. **Adding a route without updating `ROUTE_TO_FLOW`** → flow drift check fails in pre-commit.
3. **Defining an exception without registering it in `ALL_ERROR_MAPPING`** → the API returns a generic 500 instead of the right status code.
4. **Mocking the DB in integration tests** → forbidden, will be flagged in PR review.
5. **Touching `specs/` without updating the registry** → pre-commit hook fails. If you really need to change a flow, do it in the `TBG-AI/docs` repo first, then update the submodule.

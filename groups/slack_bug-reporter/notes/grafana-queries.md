# Grafana query reference

Quick reference for common BugReporter queries. All driven via `GrafanaClient` in [`nanoclaw/groups/slack_bug-reporter/scripts/grafana_query.py`](../../../nanoclaw/groups/slack_bug-reporter/scripts/grafana_query.py).

## Connection

- **Host**: `https://vxbrandon00.grafana.net`
- **Auth**: `GRAFANA_SA_TOKEN` env var (service account token)
- **Datasources**:
  - Prometheus: id `3`
  - Loki: id `12`
  - Tempo: id `5`
- **Services monitored**: `backend-server`, `backend-odds`

## Logs (Loki)

### Recent 5xx errors
```logql
{service=~"backend-server|backend-odds"} |= "ERROR" | json | level = "ERROR"
```

### All logs for a specific request
```logql
{service=~"backend-server|backend-odds"} | json | request_id = "<id>"
```

### Errors by type
```logql
{service="backend-server"} | json | err_type = "NullOddsError"
```

### Errors on a specific endpoint
```logql
{service="backend-server"} | json | endpoint = "/api/v1/bets/place" | level = "ERROR"
```

### Count by user (for blast-radius)
```logql
sum by (user_id) (
  count_over_time({service="backend-server"} | json | err_type = "NullOddsError" [1h])
)
```

## Metrics (Prometheus)

### Error rate per service
```promql
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  /
sum by (service) (rate(http_requests_total[5m]))
```

### Error rate per endpoint
```promql
sum by (endpoint) (rate(http_requests_total{service="backend-server", status=~"5.."}[5m]))
```

### p99 latency
```promql
histogram_quantile(0.99,
  sum by (le, endpoint) (rate(http_request_duration_seconds_bucket{service="backend-server"}[5m]))
)
```

## Traces (Tempo)

### Fetch trace by ID
Via `GrafanaClient.get_trace_by_id(trace_id)`. Returns the full span tree.

### Find recent error traces
```
{ status = error }
```

### Find slow traces
```
{ duration > 5s }
```

## Known error patterns

| Error type | Service | Typical cause | Code location |
|---|---|---|---|
| `NullOddsError` | backend-server | Odds microservice returns null for a parlay leg | `infrastructure/microservices/odds_client.py` |
| `ConnectionTimeout` | backend-odds | Kalshi API slow response | `infrastructure/external/kalshi/client.py` |
| `ValidationError` (Pydantic) | backend-server | Frontend sending malformed request body | `application/schemas/requests/` |
| `DatabaseError: deadlock` | backend-server | Concurrent bet settlement on same event | `application/services/bets/user_bet_service.py` |
| `KeyError: 'session_id'` | both | Request missing session middleware | `infrastructure/middleware/request_id.py` |

**Add new patterns here** when you identify one during a scan.

## Known hotspots

Files that generate disproportionate error volume. Flag these in reports if they surface:

- `src/backend_server/application/services/bets/user_bet_service.py` — bet placement / settlement hot path
- `src/backend_server/infrastructure/microservices/odds_client.py` — cross-service boundary
- `src/backend_odds/infrastructure/external/kalshi/client.py` — external API boundary
- `src/backend_server/infrastructure/api/rest/bet_routes.py` — heavy endpoint traffic

## Flow context lookup

When a log entry has a `flow` field, look it up in `Backend-Server/specs/flows/flow-registry.json` to understand the business context. Common flows:

- `bets.place_single` / `bets.place_parlay`
- `bets.settle`
- `odds.fetch` / `odds.cache_refresh`
- `payments.deposit` / `payments.withdraw`
- `auth.signup` / `auth.login`
- `users.kyc`

If a log entry has no `flow`, something is wrong with instrumentation → file a `needs-instrumentation` issue.

## Useful Grafana UI links

Pre-filled dashboards to share in Slack reports:

- [24h errors dashboard](https://vxbrandon00.grafana.net/d/tbg-errors)
- [Endpoint latency heatmap](https://vxbrandon00.grafana.net/d/tbg-latency)
- [Flow overview](https://vxbrandon00.grafana.net/d/tbg-flows)

*(URLs here are illustrative — update when the dashboards exist.)*

# Grafana Cloud Query Reference

## Bug Detection Workflow

1. **Check error rate**: `python3 /workspace/group/scripts/grafana_query.py error-rate`
2. **If errors exist**: `python3 /workspace/group/scripts/grafana_query.py errors --minutes 60`
3. **For each unique error**: Look at `error_type`, `endpoint`, and `stack_trace`
4. **Correlate with trace**: `python3 /workspace/group/scripts/grafana_query.py trace <trace_id>`
5. **Generate report**: `python3 /workspace/group/scripts/grafana_query.py report --minutes 60`

## CLI Reference

```bash
# Full bug report (metrics + logs + traces)
python3 /workspace/group/scripts/grafana_query.py report --minutes 60

# Get recent 500 errors with stack traces
python3 /workspace/group/scripts/grafana_query.py errors --minutes 60 --limit 50

# Check current error rate (per second)
python3 /workspace/group/scripts/grafana_query.py error-rate

# Total 5xx error count
python3 /workspace/group/scripts/grafana_query.py error-count --minutes 60

# Full trace details by trace ID
python3 /workspace/group/scripts/grafana_query.py trace <trace_id>

# All logs for a specific request
python3 /workspace/group/scripts/grafana_query.py request <request_id>
```

## Python API

```python
from scripts.grafana_query import GrafanaClient
client = GrafanaClient()

resp = client.get_recent_500_errors(minutes=60)
errors = client.parse_error_logs(resp)
# Fields: timestamp, level, message, file, function, line_number,
#   trace_id, span_id, error_type, error_message, stack_trace, endpoint

report = client.generate_bug_report(minutes=60)
```

## Known Error Patterns in Backend-Server

### Error Types (from ALL_ERROR_MAPPING in app.py)
- `OddsMicroserviceRequestError` — Odds service is down/returning errors
- `StreamingServiceTimeoutError` — Streaming service timeout (504)
- `HTTPException` — Generic HTTP errors
- `InsufficientBalanceError` — User doesn't have enough balance (402)
- `TournamentNotFoundError` — Tournament not found (404)

### Error Code Format
- Mapped errors: `TOURNAMENT_NOT_FOUND`, `INSUFFICIENT_BALANCE`, etc.
- Unmapped 500s: `UNEXPECTED_{EXCEPTION_CLASS_NAME_UPPER}` (e.g., `UNEXPECTED_ODDSMICROSERVICEREQUESTERROR`)

### Key Endpoints
- `/bets/generate_bet` — Bet generation (calls odds microservice)
- `/bets/place_bet` — Bet placement
- `/users/kyc/session` — KYC verification
- `/transactions_v1/` — Payment processing
- `/auth/` — Authentication

## Backend-Server Code Locations

| Area | File |
|------|------|
| Exception handlers | `src/backend_server/app.py` (lines 216-407) |
| Error mapping | `src/backend_server/infrastructure/api/rest/constants.py` |
| Odds client | `src/backend_server/infrastructure/microservices/odds_client.py` |
| Bet service | `src/backend_server/application/services/bets/user_bet_service.py` |
| Bet routes | `src/backend_server/infrastructure/api/rest/bet_routes.py` |
| Metrics middleware | `src/backend_server/infrastructure/middleware/metrics_middleware.py` |

## Grafana Config

- Instance: vxbrandon00.grafana.net
- Datasource IDs: Prometheus=3, Loki=12, Tempo=5
- Token: set via GRAFANA_SA_TOKEN env var (see settings.json)

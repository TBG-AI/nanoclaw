#!/usr/bin/env python3
"""
Grafana Cloud Query Library for Bug Reporter Agent.

Usage:
    from grafana_query import GrafanaClient
    client = GrafanaClient()
    errors = client.get_recent_500_errors(minutes=60)
    report = client.generate_bug_report(minutes=60)
"""

import json
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone


GRAFANA_HOST = "https://vxbrandon00.grafana.net"
GRAFANA_SA_TOKEN = os.environ.get("GRAFANA_SA_TOKEN", "")

# Datasource IDs
DS_PROMETHEUS = 3
DS_LOKI = 12
DS_TEMPO = 5

# Services to monitor
SERVICES = ["backend-server", "backend-odds"]
SERVICE_REGEX = "|".join(SERVICES)  # "backend-server|backend-odds"


class GrafanaClient:
    def __init__(self, token=None, host=None):
        self.token = token or GRAFANA_SA_TOKEN
        self.host = host or GRAFANA_HOST
        self.proxy_base = f"{self.host}/api/datasources/proxy"

    def _request(self, url, params=None):
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            result = subprocess.run(
                ["curl", "-s", "-H", f"Authorization: Bearer {self.token}", url],
                capture_output=True, text=True, timeout=30,
            )
            return json.loads(result.stdout) if result.stdout.strip() else {"error": "empty response"}
        except subprocess.TimeoutExpired:
            return {"error": "request timed out"}
        except json.JSONDecodeError:
            return {"error": f"invalid JSON: {result.stdout[:200]}"}

    # =========================================================
    # LOKI (Logs)
    # =========================================================

    def _loki_query(self, logql, minutes=60, limit=50):
        now_ns = int(time.time() * 1e9)
        start_ns = int((time.time() - minutes * 60) * 1e9)
        return self._request(
            f"{self.proxy_base}/{DS_LOKI}/loki/api/v1/query_range",
            {
                "query": logql,
                "start": str(start_ns),
                "end": str(now_ns),
                "limit": str(limit),
            },
        )

    def _svc_filter(self, service=None):
        """Return Loki label filter for service_name."""
        if service:
            return f'service_name="{service}"'
        return f'service_name=~"{SERVICE_REGEX}"'

    def get_recent_500_errors(self, minutes=60, limit=50, service=None):
        """Get recent 500/UNEXPECTED errors from logs (all services by default)."""
        svc = self._svc_filter(service)
        return self._loki_query(
            f'{{{svc}}} |= "UNEXPECTED error"',
            minutes=minutes,
            limit=limit,
        )

    def get_error_logs(self, minutes=60, limit=50, service=None):
        """Get all ERROR-level logs (all services by default)."""
        svc = self._svc_filter(service)
        return self._loki_query(
            f'{{{svc}, severity_text="ERROR"}}',
            minutes=minutes,
            limit=limit,
        )

    def get_logs_by_request_id(self, request_id, hours=24):
        """Get all logs for a specific request ID (searches all services)."""
        svc = self._svc_filter()
        return self._loki_query(
            f'{{{svc}}} |= "{request_id}"',
            minutes=hours * 60,
            limit=100,
        )

    def get_endpoint_errors(self, endpoint, minutes=60, limit=50, service=None):
        """Get errors for a specific API endpoint."""
        svc = self._svc_filter(service)
        return self._loki_query(
            f'{{{svc}, severity_text="ERROR"}} |= "{endpoint}"',
            minutes=minutes,
            limit=limit,
        )

    def get_errors_by_type(self, error_type, minutes=60, limit=50, service=None):
        """Get errors by exception type (e.g. ValueError, TimeoutError)."""
        svc = self._svc_filter(service)
        return self._loki_query(
            f'{{{svc}, exception_type="{error_type}"}}',
            minutes=minutes,
            limit=limit,
        )

    # =========================================================
    # PROMETHEUS/MIMIR (Metrics)
    # =========================================================

    def _prom_query(self, promql):
        return self._request(
            f"{self.proxy_base}/{DS_PROMETHEUS}/api/v1/query",
            {"query": promql},
        )

    def _prom_range_query(self, promql, hours=6, step=60):
        now = int(time.time())
        start = int(time.time() - hours * 3600)
        return self._request(
            f"{self.proxy_base}/{DS_PROMETHEUS}/api/v1/query_range",
            {"query": promql, "start": str(start), "end": str(now), "step": str(step)},
        )

    def _svc_job_filter(self, service=None):
        """Return PromQL job label filter.
        Both services use OTEL auto-instrumented metrics with job='tbg/{service}'.
        """
        if service:
            return f'job="tbg/{service}"'
        return f'job=~"tbg/({SERVICE_REGEX})"'

    def get_error_rate(self, service=None):
        """Current 5xx error rate (per second, 5m window)."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'sum by (service_name) (rate(http_server_duration_milliseconds_count{{{job},http_status_code=~"5.."}}[5m]))'
        )

    def get_error_rate_by_endpoint(self, service=None):
        """5xx error rate broken down by endpoint."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'sum by (service_name, http_target) (rate(http_server_duration_milliseconds_count{{{job},http_status_code=~"5.."}}[5m]))'
        )

    def get_error_count(self, minutes=60, service=None):
        """Total 5xx error count over last N minutes."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'sum by (service_name) (increase(http_server_duration_milliseconds_count{{{job},http_status_code=~"5.."}}[{minutes}m]))'
        )

    def get_error_count_by_endpoint(self, minutes=60, service=None):
        """5xx error count broken down by endpoint and status code."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'sum by (service_name, http_target, http_status_code) (increase(http_server_duration_milliseconds_count{{{job},http_status_code=~"5.."}}[{minutes}m]))'
        )

    def get_error_percentage(self, service=None):
        """Percentage of requests returning 5xx."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'100 * sum(rate(http_server_duration_milliseconds_count{{{job},http_status_code=~"5.."}}[5m])) / sum(rate(http_server_duration_milliseconds_count{{{job}}}[5m]))'
        )

    def get_p99_latency(self, service=None):
        """P99 latency by endpoint."""
        job = self._svc_job_filter(service)
        return self._prom_query(
            f'histogram_quantile(0.99, sum by (le, http_target) (rate(http_server_duration_milliseconds_bucket{{{job}}}[5m])))'
        )

    # =========================================================
    # WEBSOCKET METRICS (Backend-Odds specific)
    # =========================================================

    def get_websocket_errors(self, minutes=60):
        """Backend-Odds WebSocket errors."""
        return self._prom_query(
            f'sum by (message_type) (increase(websocket_message_errors_total{{job="tbg/backend-odds"}}[{minutes}m]))'
        )

    def get_websocket_connections(self):
        """Current active WebSocket connections."""
        return self._prom_query(
            'websocket_connections_active{job="tbg/backend-odds"}'
        )

    # =========================================================
    # TEMPO (Traces)
    # =========================================================

    def get_error_traces(self, limit=20, service=None):
        """Search for traces with HTTP 500 status."""
        svc_tag = f"service.name={service}" if service else "service.name=backend-server"
        return self._request(
            f"{self.proxy_base}/{DS_TEMPO}/api/search",
            {"tags": f"{svc_tag} http.status_code=500", "limit": str(limit)},
        )

    def get_slow_traces(self, min_duration_ms=5000, limit=20, service=None):
        """Search for slow traces."""
        svc_tag = f"service.name={service}" if service else "service.name=backend-server"
        return self._request(
            f"{self.proxy_base}/{DS_TEMPO}/api/search",
            {
                "tags": svc_tag,
                "minDuration": f"{min_duration_ms}ms",
                "limit": str(limit),
            },
        )

    def get_trace_by_id(self, trace_id):
        """Get full trace details by trace ID."""
        return self._request(f"{self.proxy_base}/{DS_TEMPO}/api/traces/{trace_id}")

    # =========================================================
    # HIGH-LEVEL BUG DETECTION
    # =========================================================

    def parse_error_logs(self, raw_response):
        """Parse Loki response into structured error records.

        Loki OTEL logs store rich data in stream labels (not the log line body).
        Key stream labels:
          - exception_type, exception_message, exception_stacktrace
          - trace_id / otelTraceID, span_id / otelSpanID
          - code_file_path, code_function_name, code_line_number
          - severity_text, scope_name, service_name
        The log line body is just the plain text message.
        """
        errors = []
        data = raw_response.get("data", {})
        for stream in data.get("result", []):
            labels = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                errors.append({
                    "timestamp": datetime.fromtimestamp(
                        int(ts) / 1e9, tz=timezone.utc
                    ).isoformat(),
                    "level": labels.get("severity_text", "?"),
                    "message": line,
                    "file": labels.get("code_file_path", "?"),
                    "function": labels.get("code_function_name", "?"),
                    "line_number": labels.get("code_line_number", "?"),
                    "trace_id": labels.get("trace_id", labels.get("otelTraceID", "?")),
                    "span_id": labels.get("span_id", labels.get("otelSpanID", "?")),
                    "error_type": labels.get("exception_type", ""),
                    "error_message": labels.get("exception_message", ""),
                    "stack_trace": labels.get("exception_stacktrace", ""),
                    "endpoint": _extract_endpoint(line),
                    "scope": labels.get("scope_name", ""),
                    "environment": labels.get("deployment_environment", ""),
                    "service": labels.get("service_name", "unknown"),
                })
        return errors

    def parse_metric_result(self, raw_response):
        """Parse Prometheus instant query result."""
        data = raw_response.get("data", {})
        results = []
        for r in data.get("result", []):
            metric = r.get("metric", {})
            value = r.get("value", [None, None])
            results.append({
                "labels": metric,
                "value": float(value[1]) if value[1] and value[1] != "NaN" else 0,
            })
        return results

    def generate_bug_report(self, minutes=60):
        """Generate a comprehensive bug report for the last N minutes."""
        report = {
            "time_window": f"Last {minutes} minutes",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Error count
        count_resp = self.get_error_count(minutes)
        count_data = self.parse_metric_result(count_resp)
        report["total_5xx_errors"] = count_data[0]["value"] if count_data else 0

        # 2. Error rate
        rate_resp = self.get_error_rate()
        rate_data = self.parse_metric_result(rate_resp)
        report["current_error_rate_per_sec"] = rate_data[0]["value"] if rate_data else 0

        # 3. Error percentage
        pct_resp = self.get_error_percentage()
        pct_data = self.parse_metric_result(pct_resp)
        report["error_percentage"] = pct_data[0]["value"] if pct_data else 0

        # 4. Errors by endpoint
        by_ep_resp = self.get_error_count_by_endpoint(minutes)
        by_ep_data = self.parse_metric_result(by_ep_resp)
        report["errors_by_endpoint"] = [
            {
                "service": r["labels"].get("service_name", "unknown"),
                "endpoint": r["labels"].get("http_target", "unknown"),
                "status_code": r["labels"].get("http_status_code", "5xx"),
                "count": r["value"],
            }
            for r in sorted(by_ep_data, key=lambda x: x["value"], reverse=True)
            if r["value"] > 0
        ]

        # 5. Recent error logs with details
        logs_resp = self.get_recent_500_errors(minutes=minutes, limit=20)
        errors = self.parse_error_logs(logs_resp)
        report["recent_errors"] = errors

        # 6. Error traces
        traces_resp = self.get_error_traces(limit=10)
        traces = traces_resp.get("traces", [])
        report["error_traces"] = [
            {
                "trace_id": t.get("traceID"),
                "root_service": t.get("rootServiceName"),
                "root_span": t.get("rootTraceName"),
                "duration_ms": t.get("durationMs"),
            }
            for t in traces
        ]

        return report


def _extract_endpoint(msg):
    """Extract endpoint path from error message like 'UNEXPECTED error at /bets/place_bet: ...'"""
    if "error at " in msg:
        parts = msg.split("error at ")
        if len(parts) > 1:
            path = parts[1].split(":")[0].strip()
            return path
    return ""


# =========================================================
# CLI
# =========================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Grafana Cloud Bug Reporter Queries")
    sub = parser.add_subparsers(dest="command")

    # report
    p = sub.add_parser("report", help="Generate full bug report")
    p.add_argument("--minutes", type=int, default=60)

    # errors
    p = sub.add_parser("errors", help="Get recent 500 errors")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--limit", type=int, default=20)

    # error-rate
    sub.add_parser("error-rate", help="Current error rate")

    # error-count
    p = sub.add_parser("error-count", help="Error count")
    p.add_argument("--minutes", type=int, default=60)

    # trace
    p = sub.add_parser("trace", help="Get trace by ID")
    p.add_argument("trace_id")

    # request
    p = sub.add_parser("request", help="Get logs by request ID")
    p.add_argument("request_id")

    # slow-traces — fetch traces above a duration threshold from Tempo
    p = sub.add_parser(
        "slow-traces",
        help="Find traces slower than a duration threshold (Tempo)",
    )
    p.add_argument(
        "--min-duration-ms",
        type=int,
        default=1000,
        help="Minimum duration in ms (default: 1000)",
    )
    p.add_argument("--limit", type=int, default=20)
    p.add_argument(
        "--service",
        default=None,
        help="Service name (default: backend-server)",
    )

    # slow-endpoints — list endpoints by p95/p99 over a window (Prometheus)
    p = sub.add_parser(
        "slow-endpoints",
        help="List endpoints sorted by p95/p99 latency (Prometheus)",
    )
    p.add_argument(
        "--minutes",
        type=int,
        default=15,
        help="Window in minutes for the rate (default: 15)",
    )
    p.add_argument(
        "--service",
        default="backend-server",
        help="Service name (default: backend-server)",
    )
    p.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of endpoints to return (default: 10)",
    )
    p.add_argument(
        "--quantile",
        type=float,
        default=0.95,
        choices=[0.50, 0.90, 0.95, 0.99],
        help="Latency quantile to rank by (default: 0.95)",
    )

    # p99 — current p99 latency for a service (single number)
    p = sub.add_parser("p99", help="Current p99 latency for a service")
    p.add_argument(
        "--service",
        default="backend-server",
        help="Service name (default: backend-server)",
    )

    args = parser.parse_args()
    client = GrafanaClient()

    if args.command == "report":
        report = client.generate_bug_report(minutes=args.minutes)
        print(json.dumps(report, indent=2))

    elif args.command == "errors":
        resp = client.get_recent_500_errors(minutes=args.minutes, limit=args.limit)
        errors = client.parse_error_logs(resp)
        for e in errors:
            print(f"\n{'='*60}")
            print(f"[{e['timestamp']}] {e['error_type']}")
            print(f"  Message: {e['message']}")
            print(f"  Error: {e['error_message'][:200]}")
            print(f"  Endpoint: {e['endpoint']}")
            print(f"  File: {e['file']}:{e['line_number']} ({e['function']})")
            print(f"  Trace ID: {e['trace_id']}")
            if e["stack_trace"]:
                # Show last few meaningful lines of stack trace
                stack_lines = [l for l in e['stack_trace'].split('\n') if l.strip() and '/app/' in l]
                if stack_lines:
                    print(f"  App stack frames:")
                    for sl in stack_lines[-5:]:
                        print(f"    {sl.strip()}")
        if not errors:
            print("No 500 errors found in the time window.")

    elif args.command == "error-rate":
        resp = client.get_error_rate()
        data = client.parse_metric_result(resp)
        rate = data[0]["value"] if data else 0
        print(f"Current 5xx error rate: {rate:.4f} req/s")

    elif args.command == "error-count":
        resp = client.get_error_count(args.minutes)
        data = client.parse_metric_result(resp)
        count = data[0]["value"] if data else 0
        print(f"5xx errors in last {args.minutes}m: {count:.0f}")

    elif args.command == "trace":
        resp = client.get_trace_by_id(args.trace_id)
        print(json.dumps(resp, indent=2))

    elif args.command == "request":
        resp = client.get_logs_by_request_id(args.request_id)
        errors = client.parse_error_logs(resp)
        for e in errors:
            print(f"[{e['timestamp']}] [{e['level']}] {e['message']}")
        if not errors:
            print("No logs found for this request ID.")

    elif args.command == "slow-traces":
        resp = client.get_slow_traces(
            min_duration_ms=args.min_duration_ms,
            limit=args.limit,
            service=args.service,
        )
        traces = resp.get("traces", []) if isinstance(resp, dict) else []
        if not traces:
            print(
                f"No traces found above {args.min_duration_ms}ms "
                f"for service={args.service or 'backend-server'}."
            )
        else:
            print(
                f"Slow traces (>{args.min_duration_ms}ms) "
                f"for service={args.service or 'backend-server'} — top {len(traces)}:"
            )
            print(f"{'duration_ms':>11s}  {'trace_id':32s}  {'root_span':40s}  {'started_at'}")
            print("-" * 110)
            # Tempo trace search response shape varies by version. Try a couple
            # of common field names so this still works as the API evolves.
            for t in traces:
                tid = t.get("traceID") or t.get("trace_id") or "?"
                dur = t.get("durationMs") or t.get("duration_ms")
                if dur is None:
                    # Some Tempo responses give duration in nanoseconds
                    dur_ns = t.get("durationNs") or t.get("duration") or 0
                    try:
                        dur = int(dur_ns) / 1_000_000
                    except Exception:
                        dur = 0
                root = t.get("rootServiceName", "") + " " + t.get("rootTraceName", "")
                root = root.strip()[:40]
                started = (
                    t.get("startTimeUnixNano")
                    or t.get("start_time_unix_nano")
                    or t.get("startTime", "")
                )
                # Convert ns timestamp to ISO if it looks like a number
                if isinstance(started, (int, str)) and str(started).isdigit():
                    try:
                        from datetime import datetime, timezone
                        started = datetime.fromtimestamp(
                            int(started) / 1e9, tz=timezone.utc
                        ).isoformat(timespec="seconds")
                    except Exception:
                        pass
                print(f"{dur:>11.0f}  {tid:32s}  {root:40s}  {started}")

    elif args.command == "slow-endpoints":
        # Run a histogram_quantile query directly via Prom proxy.
        # The exact metric name depends on instrumentation; try the OTEL
        # http_server_duration_milliseconds_bucket first.
        promql = (
            f'topk({args.top}, '
            f'histogram_quantile({args.quantile}, '
            f'sum by (le, http_route, http_method) ('
            f'rate(http_server_duration_milliseconds_bucket'
            f'{{service_name="{args.service}"}}[{args.minutes}m]))))'
        )
        resp = client._prom_query(promql)
        data = client.parse_metric_result(resp)
        if not data:
            print(
                f"No latency data found for service={args.service} "
                f"window={args.minutes}m. The metric "
                f"http_server_duration_milliseconds_bucket may be missing — "
                f"check that OTEL auto-instrumentation is enabled."
            )
        else:
            qpct = int(args.quantile * 100)
            print(
                f"Top {args.top} endpoints by p{qpct} latency "
                f"(service={args.service}, window={args.minutes}m):"
            )
            print(f"{'p' + str(qpct) + ' (ms)':>10s}  {'method':6s}  {'route'}")
            print("-" * 80)
            # Sort descending by value
            sorted_rows = sorted(
                data, key=lambda r: float(r.get("value", 0) or 0), reverse=True
            )
            for row in sorted_rows[: args.top]:
                labels = row.get("labels", {}) or row.get("metric", {})
                # parse_metric_result returns either dict shape; handle both
                if isinstance(row, dict) and "metric" in row:
                    labels = row.get("metric", {})
                route = labels.get("http_route") or labels.get("route", "?")
                method = labels.get("http_method") or labels.get("method", "?")
                val = float(row.get("value", 0) or 0)
                print(f"{val:>10.0f}  {method:6s}  {route}")

    elif args.command == "p99":
        resp = client.get_p99_latency(service=args.service)
        data = client.parse_metric_result(resp)
        if not data:
            print(f"No latency data for service={args.service}")
        else:
            for row in data:
                metric = row.get("metric", {}) if isinstance(row, dict) else {}
                val = float(row.get("value", 0) or 0)
                ep = (
                    metric.get("http_route")
                    or metric.get("endpoint")
                    or metric.get("http_target")
                    or "all"
                )
                print(f"  {val:>10.0f}ms  {ep}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

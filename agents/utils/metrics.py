from __future__ import annotations

from prometheus_client import Counter, Histogram

# Gamma API metrics
gamma_requests_total = Counter(
    "gamma_requests_total",
    "Total requests to Gamma API",
    labelnames=("endpoint", "status"),
)

gamma_cache_hits_total = Counter(
    "gamma_cache_hits_total",
    "Cache hits for Gamma data",
    labelnames=("resource",),
)

# Trading metrics (dry-run/live)
trades_total = Counter(
    "trades_total",
    "Total number of executed trades",
    labelnames=("mode",),
)

pnl_histogram = Histogram(
    "trade_pnl",
    "PnL distribution per trade",
    buckets=(-100.0, -50.0, -20.0, -10.0, -5.0, -2.0, -1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0),
)



"""
Prometheus metrics for the Enterprise API.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Summary

# Total request counter, labeled by decision type
request_counter = Counter(
    "promptshield_requests_total",
    "Total number of precheck requests processed",
    labelnames=["decision", "model", "source"],
)

# Decision distribution counter
decision_counter = Counter(
    "promptshield_decisions_total",
    "Count of decisions by type",
    labelnames=["decision"],
)

# Request processing duration
request_duration = Histogram(
    "promptshield_request_duration_seconds",
    "Time spent processing a precheck request",
    labelnames=["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# Token usage summary
token_usage = Summary(
    "promptshield_tokens_used",
    "Distribution of total tokens per request",
)

# Cost distribution
cost_distribution = Histogram(
    "promptshield_estimated_cost_usd",
    "Distribution of estimated costs per request",
    buckets=[0.0001, 0.001, 0.01, 0.05, 0.10, 0.25, 0.50, 1.0],
)

# Misuse score distribution
misuse_score_histogram = Histogram(
    "promptshield_misuse_score",
    "Distribution of misuse scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

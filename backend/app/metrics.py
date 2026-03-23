"""Prometheus metrics for the multi-agent orchestrator (exposed via /metrics on the app)."""

from prometheus_client import Counter, Histogram

agent_calls_total = Counter(
    "vyezdnik_agent_calls_total",
    "Invocations of individual agents and graph nodes",
    ["agent", "outcome"],
)

agent_duration_seconds = Histogram(
    "vyezdnik_agent_duration_seconds",
    "Wall-clock duration of agent and graph node execution",
    ["agent"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

orchestrator_runs_total = Counter(
    "vyezdnik_orchestrator_runs_total",
    "Completed orchestrator graph runs",
    ["result"],
)

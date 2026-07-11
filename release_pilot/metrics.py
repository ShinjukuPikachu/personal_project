from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "release_pilot_http_requests_total",
    "Total number of HTTP requests",
    labelnames=("method", "path", "status"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "release_pilot_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path"),
)

RELEASE_GENERATION_TOTAL = Counter(
    "release_pilot_release_generation_total",
    "Total release-generation attempts",
    labelnames=("status",),
)

RELEASE_GENERATION_DURATION_SECONDS = Histogram(
    "release_pilot_release_generation_duration_seconds",
    "Time spent generating a release",
)

AI_AGENT_EXECUTIONS_TOTAL = Counter(
    "release_pilot_ai_agent_executions_total",
    "Total AI-agent executions",
    labelnames=("agent", "status"),
)

AI_AGENT_DURATION_SECONDS = Histogram(
    "release_pilot_ai_agent_duration_seconds",
    "AI-agent execution duration",
    labelnames=("agent",),
)

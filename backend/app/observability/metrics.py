from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled by the API",
    ("method", "path", "status"),
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ("method", "path"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 12, 30),
)
LLM_REQUESTS = Counter("llm_requests_total", "Provider requests", ("provider", "model", "status"))
LLM_DURATION = Histogram(
    "llm_request_duration_seconds",
    "Provider request duration",
    ("provider", "model"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 12, 20),
)
LLM_FAILURES = Counter(
    "llm_failures_total", "Provider failures after retries", ("provider", "reason")
)
PROVIDER_RETRY_ATTEMPTS = Counter(
    "provider_retry_attempts_total",
    "Provider operations after the initial attempt",
    ("provider", "model"),
)
PROVIDER_ATTEMPT_DURATION = Histogram(
    "provider_attempt_duration_seconds",
    "Duration of each application-managed provider attempt",
    ("provider", "model", "outcome"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 12, 15),
)
LLM_FALLBACK = Counter("llm_fallback_total", "Fallback assessments", ("primary", "fallback"))
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Provider circuit state: closed=0, half_open=0.5, open=1",
    ("provider",),
)
CACHE_HITS = Counter("cache_hits_total", "Assessment cache hits", ("provider",))
CACHE_MISSES = Counter("cache_misses_total", "Assessment cache misses", ("provider",))
INCIDENT_ASSESSMENTS = Counter(
    "incident_assessments_total",
    "Persisted incident assessments",
    ("severity", "provider", "fallback"),
)
READINESS_FAILURES = Counter(
    "readiness_check_failures_total", "Failed readiness dependency checks", ("dependency",)
)
ANALYSIS_FAILURES = Counter(
    "analysis_failures_total", "Valid analysis requests that ended in an unrecovered server error"
)

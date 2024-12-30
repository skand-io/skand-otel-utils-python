from __future__ import annotations

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def get_traceparent_from_current_trace_context() -> str | None:
    """Get traceparent from current trace context."""
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier.get(TraceContextTextMapPropagator._TRACEPARENT_HEADER_NAME)  # noqa: SLF001

from __future__ import annotations

import functools
import json
import logging
from typing import TYPE_CHECKING, Callable, Sequence

from opentelemetry import context, trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

if TYPE_CHECKING:
    from cloudevents.sdk.event import v1
    from dapr.clients.grpc._response import TopicEventResponse

    from skand_otel_utils.cloudevents.types import CloudEventHandler


class TraceparentExtractor:
    """Pipeline for extracting traceparent from different sources in an event."""

    @staticmethod
    def from_extensions(event: v1.Event) -> str | None:
        """Extract traceparent from event extensions."""
        traceparent = event.extensions.get("traceparent")
        if not traceparent:
            logging.warning("Not found traceparent from event extensions")
        return traceparent

    @staticmethod
    def from_json_data(event: v1.Event) -> str | None:
        """Extract traceparent from JSON event data."""
        try:
            event_data: object = json.loads(event.data)
        except (json.JSONDecodeError, TypeError) as e:
            msg = f"Failed to parse event data for traceparent: {e}"
            logging.warning(msg)
            return None

        if not isinstance(event_data, dict):
            return None

        traceparent = event_data.get("traceparent")
        if not traceparent:
            logging.warning("Not found traceparent from event data")
        return traceparent

    @classmethod
    def get_default_pipelines(cls) -> Sequence[Callable[[v1.Event], str | None]]:
        """Return the default pipeline functions for traceparent extraction."""
        return (
            cls.from_json_data,
            cls.from_extensions,
        )


def _extract_trace_context_from_traceparent(traceparent: str) -> trace.Context:
    """Extract trace context from a W3C traceparent string.

    Args:
        traceparent (str): W3C traceparent string (e.g., '00-trace-id-span-id-flags')

    Returns:
        trace.Context: The extracted trace context containing span and trace information

    """
    propagator = TraceContextTextMapPropagator()
    return propagator.extract({"traceparent": traceparent})


def _attach_distributed_trace_context(trace_context: trace.Context) -> object | None:
    """Attach distributed tracing context from a traceparent string."""
    span_context = trace.get_current_span(trace_context).get_span_context()
    if span_context.is_valid and span_context.is_remote:
        return context.attach(trace_context)
    return None


def setup_distributed_trace_context(
    pipelines: Sequence[CloudEventHandler] | None = None,
) -> Callable[[CloudEventHandler], CloudEventHandler]:
    """Configure traceparent extraction pipelines.

    Args:
        pipelines: Sequence of extractor functions that take a CloudEvent and
            return an optional traceparent string. Defaults to standard extractors
        if None.

    """
    if pipelines is None:
        pipelines = TraceparentExtractor.get_default_pipelines()

    def decorator(func: CloudEventHandler) -> CloudEventHandler:
        @functools.wraps(func)
        def wrapper(event: v1.Event) -> TopicEventResponse:
            # Extract traceparent using configured pipelines
            traceparent = None
            for extractor in pipelines:
                traceparent = extractor(event)
                if traceparent:
                    logging.info(
                        "found traceparent in extractor: %s", extractor.__name__
                    )
                    break

            token = None
            if traceparent:
                logging.info("Extracted traceparent: %s", traceparent)
                trace_context = _extract_trace_context_from_traceparent(traceparent)
                token = _attach_distributed_trace_context(trace_context)
            else:
                logging.error("Failed to extract traceparent from the event.")

            result = func(event)

            if token:
                context.detach(token)
            return result

        return wrapper

    return decorator

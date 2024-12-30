import functools
import json
from typing import Any, Callable

from cloudevents.sdk.event import v1
from dapr.clients.grpc._response import TopicEventResponse, TopicEventResponseStatus
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from skand_otel_utils.cloudevents.types import CloudEventHandler


def set_span_status_from_cloudenvet_handler_result(
    func: CloudEventHandler,
) -> Callable[[CloudEventHandler], CloudEventHandler]:
    """Set the span status based on the result of the CloudEvent handler."""

    @functools.wraps(func)
    def wrapper(event: v1.Event) -> TopicEventResponse:
        result: TopicEventResponse = func(event)
        if not isinstance(result, TopicEventResponse):
            return result

        status_code = (
            StatusCode.OK
            if result.status == TopicEventResponseStatus.success
            else trace.StatusCode.ERROR
        )
        span = trace.get_current_span()
        span.set_status(status_code)
        return result

    return wrapper


def set_span_event_from_event(
    name: str,
    event_extractor: Callable[[v1.Event], Any],
) -> Callable[[CloudEventHandler], CloudEventHandler]:
    """Wrap a function with a trace span.

    Args:
        name: Name of the span
        event_extractor: Function to extract data from the event for span attributes

    """

    def decorator(func: CloudEventHandler) -> CloudEventHandler:
        @functools.wraps(func)
        def wrapper(event: v1.Event) -> TopicEventResponse:
            span = trace.get_current_span()
            span.add_event(name, event_extractor(event))
            return func(event)

        return wrapper

    return decorator


def extract_payload_from_cloudevent(event: v1.Event) -> dict:
    """Create a dictionary representation of the event payload."""
    return {
        "event_data_type": type(event.data).__name__,
        "event_data": str(event.data),
        "event_type": event.type,
        "event_id": event.id,
        "event_content_type": event.content_type,
        "event_source": event.source,
        "event_extensions": json.dumps(event.extensions),
        "event_subject": event.subject,
    }

from cloudevents.sdk.event import v1
from opentelemetry import trace
from opentelemetry.context.context import Context
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.trace import (
    DEFAULT_TRACE_OPTIONS,
    DEFAULT_TRACE_STATE,
    TraceFlags,
    TraceState,
    span,
)
from opentelemetry.trace.span import SpanContext


class SpanContextBuilder:
    """Builder class for creating SpanContext instances for testing."""

    def __init__(self) -> None:
        """Initialize the SpanContextBuilder with default values."""
        id_generator = RandomIdGenerator()
        self._trace_id = id_generator.generate_trace_id()
        self._span_id = id_generator.generate_span_id()
        self._is_remote = False
        self._trace_flags = DEFAULT_TRACE_OPTIONS
        self._trace_state = DEFAULT_TRACE_STATE

    def with_trace_id(self, trace_id: int) -> "SpanContextBuilder":
        self._trace_id = trace_id
        return self

    def with_span_id(self, span_id: int) -> "SpanContextBuilder":
        self._span_id = span_id
        return self

    def with_remote(self, is_remote: bool = True) -> "SpanContextBuilder":
        self._is_remote = is_remote
        return self

    def with_trace_flags(self, trace_flags: TraceFlags) -> "SpanContextBuilder":
        self._trace_flags = trace_flags
        return self

    def with_trace_state(self, trace_state: TraceState) -> "SpanContextBuilder":
        self._trace_state = trace_state
        return self

    def build(self) -> SpanContext:
        return SpanContext(
            trace_id=self._trace_id,
            span_id=self._span_id,
            is_remote=self._is_remote,
            trace_flags=self._trace_flags,
            trace_state=self._trace_state,
        )

    def build_span(self) -> span.Span:
        return span.NonRecordingSpan(self.build())

    def build_trace_context(self) -> Context:
        return trace.set_span_in_context(self.build_span())

    def build_invalid_span_context(self) -> trace.SpanContext:
        return span.INVALID_SPAN_CONTEXT

    def build_invalid_span(self) -> span.Span:
        return span.INVALID_SPAN

    def build_invalid_trace_context(self) -> Context:
        return trace.set_span_in_context(span.INVALID_SPAN)


def format_traceparent_from_span_context(span_context: SpanContext) -> str:
    """Format a traceparent string from a SpanContext."""
    formatted_trace_id = span.format_trace_id(span_context.trace_id)
    formatted_span_id = span.format_span_id(span_context.span_id)
    return f"00-{formatted_trace_id}-{formatted_span_id}-{span_context.trace_flags:02x}"


class CloudEventBuilder:
    """Builder class for creating CloudEvent instances for testing."""

    def __init__(self) -> None:
        """Initialize the CloudEventBuilder with default values."""
        self._event = v1.Event()
        self._extensions = {}

    def with_id(self, id_: str) -> "CloudEventBuilder":
        self._event.SetEventID(id_)
        return self

    def with_source(self, source: str) -> "CloudEventBuilder":
        self._event.SetSource(source)
        return self

    def with_type(self, type_: str) -> "CloudEventBuilder":
        self._event.SetEventType(type_)
        return self

    def with_subject(self, subject: str) -> "CloudEventBuilder":
        self._event.SetSubject(subject)
        return self

    def with_content_type(self, content_type: str) -> "CloudEventBuilder":
        self._event.SetContentType(content_type)
        return self

    def with_data(self, data: object) -> "CloudEventBuilder":
        self._event.SetData(data)
        return self

    def with_extension(self, name: str, value: str) -> "CloudEventBuilder":
        self._extensions[name] = value
        self._event.SetExtensions(self._extensions)
        return self

    def build(self) -> v1.Event:
        return self._event


def assert_no_active_trace_context() -> None:
    assert trace.get_current_span().get_span_context() == span.INVALID_SPAN_CONTEXT

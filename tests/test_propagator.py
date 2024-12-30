from opentelemetry import context, trace
from opentelemetry.trace import span

from skand_otel_utils.propagator import (
    get_traceparent_from_current_trace_context,
)
from tests.testutils import (
    SpanContextBuilder,
    assert_no_active_trace_context,
    format_traceparent_from_span_context,
)


class TestGetTraceparentFromCurrentTraceContext:
    def test_happy_path_with_valid_current_trace_context(self) -> None:
        # before changing the current trace context
        assert_no_active_trace_context()

        # after changing the current trace context
        builder = SpanContextBuilder()
        token = context.attach(builder.build_trace_context())

        actual_traceparent = get_traceparent_from_current_trace_context()
        expected_from_current_span_context = format_traceparent_from_span_context(
            trace.get_current_span().get_span_context()
        )
        expected_from_input_span_context = format_traceparent_from_span_context(
            builder.build()
        )
        assert all(
            x == actual_traceparent
            for x in [
                expected_from_current_span_context,
                expected_from_input_span_context,
            ]
        )

        # teardown
        context.detach(token)
        assert_no_active_trace_context()

    def test_failure_path_with_invalid_current_trace_context(self) -> None:
        # before changing the current trace context
        assert_no_active_trace_context()

        # after changing the current trace context
        token = context.attach(SpanContextBuilder().build_invalid_trace_context())

        actual_traceparent = get_traceparent_from_current_trace_context()
        assert actual_traceparent is None

        current_span_context = trace.get_current_span().get_span_context()
        assert current_span_context == span.INVALID_SPAN_CONTEXT

        # teardown
        context.detach(token)
        assert_no_active_trace_context()

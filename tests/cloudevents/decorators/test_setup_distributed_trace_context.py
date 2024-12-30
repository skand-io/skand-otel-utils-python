from __future__ import annotations

import json
from typing import Callable

import pytest
from cloudevents.sdk.event import v1
from opentelemetry import context, trace
from opentelemetry.trace import span

from skand_otel_utils.cloudevents.decorators.setup_distributed_trace_context import (
    TraceparentExtractor,
    _attach_distributed_trace_context,
    _extract_trace_context_from_traceparent,
    setup_distributed_trace_context,
)
from tests.testutils import (
    CloudEventBuilder,
    SpanContextBuilder,
    assert_no_active_trace_context,
    format_traceparent_from_span_context,
)


class TestTraceparentExtractor:
    @pytest.mark.parametrize(
        ("setup_cloudevent", "expected_traceparent"),
        [
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_extension(
                        "traceparent",
                        "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                    )
                    .build()
                ),
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                id="happy_path",
            ),
            pytest.param(
                lambda: CloudEventBuilder().build(), None, id="empty_extensions"
            ),
            pytest.param(
                lambda: (CloudEventBuilder().with_extension("traceparent", "").build()),
                "",
                id="empty_traceparent_in_event_extensions",
            ),
        ],
    )
    def test_from_extensions(
        self, setup_cloudevent: Callable[[], v1.Event], expected_traceparent: str | None
    ) -> None:
        traceparent = TraceparentExtractor.from_extensions(setup_cloudevent())
        assert traceparent == expected_traceparent

    @pytest.mark.parametrize(
        ("setup_cloudevent", "expected_traceparent"),
        [
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(
                        json.dumps(
                            {
                                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"  # noqa: E501
                            }
                        )
                    )
                    .build()
                ),
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                id="valid_json_with_traceparent",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(json.dumps({}))
                    .build()
                ),
                None,
                id="valid_json_without_traceparent",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(json.dumps({"traceparent": ""}))
                    .build()
                ),
                "",
                id="valid_json_data_with_empty_traceparent",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(json.dumps({"traceparent": None}))
                    .build()
                ),
                None,
                id="valid_json_data_without_traceparent",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("text/plain")
                    .with_data(
                        json.dumps(
                            {
                                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"  # noqa: E501
                            }
                        )
                    )
                    .build()
                ),
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                id="valiid_json_data_with_content_type_not_application_json",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_data(
                        json.dumps(
                            {
                                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"  # noqa: E501
                            }
                        )
                    )
                    .build()
                ),
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                id="valid_json_data_without_content_type",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(None)
                    .build()
                ),
                None,
                id="null_data",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data("invalid_json_data")
                    .build()
                ),
                None,
                id="string_data",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json")
                    .with_data(123)
                    .build()
                ),
                None,
                id="number_data",
            ),
            pytest.param(
                lambda: (
                    CloudEventBuilder()
                    .with_content_type("application/json; charset=utf-8")
                    .with_data(
                        json.dumps(
                            {
                                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"  # noqa: E501
                            }
                        )
                    )
                    .build()
                ),
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                id="valid_json_data_with_charset",
            ),
        ],
    )
    def test_from_json_data(
        self, setup_cloudevent: Callable[[], v1.Event], expected_traceparent: str | None
    ) -> None:
        acutual_traceparent = TraceparentExtractor.from_json_data(setup_cloudevent())
        assert acutual_traceparent == expected_traceparent


class TestExtractTraceContextFromTraceparent:
    def test_happy_path_with_remote_span_context(self) -> None:
        before_span_context = SpanContextBuilder().with_remote(True).build()

        traceparent = format_traceparent_from_span_context(before_span_context)
        trace_context = _extract_trace_context_from_traceparent(traceparent)
        after_span_context = trace.get_current_span(trace_context).get_span_context()
        assert after_span_context == before_span_context

    def test_failing_with_non_remote_span_context(self) -> None:
        before_span_context = SpanContextBuilder().build()

        traceparent = format_traceparent_from_span_context(before_span_context)
        trace_context = _extract_trace_context_from_traceparent(traceparent)
        after_span_context = trace.get_current_span(trace_context).get_span_context()
        assert (
            before_span_context.trace_id,
            before_span_context.span_id,
            before_span_context.trace_flags,
            not before_span_context.is_remote,
        ) == (
            after_span_context.trace_id,
            after_span_context.span_id,
            after_span_context.trace_flags,
            after_span_context.is_remote,
        )

    @pytest.mark.parametrize(
        "setup_span_context",
        [
            lambda: SpanContextBuilder().with_trace_id(span.INVALID_TRACE_ID).build(),
            lambda: SpanContextBuilder().with_span_id(span.INVALID_SPAN_ID).build(),
            lambda: SpanContextBuilder().build_invalid_span_context(),
        ],
    )
    def test_failing_with_invalid_span_context(
        self, setup_span_context: Callable[[], span.SpanContext]
    ) -> None:
        before_span_context = setup_span_context()
        assert not before_span_context.is_valid

        traceparent = format_traceparent_from_span_context(before_span_context)
        trace_context = _extract_trace_context_from_traceparent(traceparent)
        after_span_context = trace.get_current_span(trace_context).get_span_context()
        assert after_span_context == span.INVALID_SPAN_CONTEXT


class TestAttachDistributedTraceContext:
    def test_valid_trace_context(self) -> None:
        span_context_builder = SpanContextBuilder().with_remote(True)
        token = _attach_distributed_trace_context(
            span_context_builder.build_trace_context()
        )
        assert token is not None

        current_span_context = trace.get_current_span().get_span_context()
        assert span_context_builder.build() == current_span_context

        # teardown
        context.detach(token)
        assert_no_active_trace_context()

    @pytest.mark.parametrize(
        "setup_trace_context",
        [
            pytest.param(
                lambda: SpanContextBuilder().build_invalid_trace_context(),
                id="invalid_trace_context",
            ),
            pytest.param(
                lambda: SpanContextBuilder()
                .with_trace_id(span.INVALID_TRACE_ID)
                .build_trace_context(),
                id="invalid_trace_id_in_trace_context",
            ),
            pytest.param(
                lambda: SpanContextBuilder()
                .with_span_id(span.INVALID_SPAN_ID)
                .build_trace_context(),
                id="invalid_span_id_in_trace_context",
            ),
            pytest.param(
                lambda: SpanContextBuilder().with_remote(False).build_trace_context(),
                id="non_remote_trace_context",
            ),
        ],
    )
    def test_invalid_trace_context(
        self, setup_trace_context: Callable[[], trace.TraceContext]
    ) -> None:
        assert _attach_distributed_trace_context(setup_trace_context()) is None


class TestSetupDistributedTraceContext:
    @pytest.mark.parametrize(
        ("pipelines", "setup_cloudevent_with_traceparent"),
        [
            pytest.param(
                (TraceparentExtractor.from_extensions,),
                lambda tp: CloudEventBuilder()
                .with_extension("traceparent", tp)
                .build(),
                id="traceparent_in_extensions",
            ),
            pytest.param(
                (TraceparentExtractor.from_json_data,),
                lambda tp: CloudEventBuilder()
                .with_data(json.dumps({"traceparent": tp}))
                .build(),
                id="traceparent_in_json_data",
            ),
            pytest.param(
                (
                    TraceparentExtractor.from_extensions,
                    TraceparentExtractor.from_json_data,
                ),
                lambda tp: CloudEventBuilder()
                .with_data(json.dumps({"traceparent": tp}))
                .build(),
                id="multiple_pipelines_first_succeeds",
            ),
            pytest.param(
                (
                    lambda _: None,
                    TraceparentExtractor.from_extensions,
                ),
                lambda tp: CloudEventBuilder()
                .with_extension("traceparent", tp)
                .build(),
                id="multiple_pipelines_second_succeeds",
            ),
        ],
    )
    def test_decorator_with_trace_propagation(
        self,
        pipelines: tuple[Callable[[v1.Event], str | None], ...],
        setup_cloudevent_with_traceparent: Callable[[str], v1.Event],
    ) -> None:
        # setup
        @setup_distributed_trace_context(pipelines)
        def cloudevent_handler(_: v1.Event) -> trace.SpanContext:
            return trace.get_current_span().get_span_context()

        remote_span_context = SpanContextBuilder().with_remote(True).build()
        traceparent = format_traceparent_from_span_context(remote_span_context)

        # before the decorator is applied
        assert_no_active_trace_context()

        # apply the decorator
        event = setup_cloudevent_with_traceparent(traceparent)
        extracted_span_context = cloudevent_handler(event)
        assert (
            extracted_span_context == remote_span_context
        ), "should refer to remote span context"

        # should no side effects after the decorator is applied
        assert_no_active_trace_context()

    @pytest.mark.parametrize(
        "pipelines",
        [
            pytest.param(None, id="cannot_find_traceparent_by_default_pipelines"),
            pytest.param((), id="empty_pipelines"),
        ],
    )
    def test_decorator_without_trace_propagation(
        self, pipelines: tuple[Callable[[v1.Event], str | None], ...]
    ) -> None:
        # setup
        @setup_distributed_trace_context(pipelines)
        def cloudevent_handler(_: v1.Event) -> trace.SpanContext:
            return trace.get_current_span().get_span_context()

        # before the decorator is applied
        assert_no_active_trace_context()

        # apply the decorator and verify no trace context is propagated
        extracted_span_context = cloudevent_handler(v1.Event())
        assert extracted_span_context == span.INVALID_SPAN_CONTEXT

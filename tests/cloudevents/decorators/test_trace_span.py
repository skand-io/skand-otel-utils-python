from __future__ import annotations

from typing import Callable

import pytest
from cloudevents.sdk.event import v1
from dapr.clients.grpc._response import TopicEventResponse, TopicEventResponseStatus
from opentelemetry.test.spantestutil import new_tracer
from opentelemetry.trace import StatusCode

from skand_otel_utils.cloudevents.decorators.trace_span import (
    extract_payload_from_cloudevent,
    set_span_event_from_event,
    set_span_status_from_cloudenvet_handler_result,
)
from tests.testutils import CloudEventBuilder


@pytest.mark.parametrize(
    ("response", "expected_span_status"),
    [
        pytest.param(
            TopicEventResponse(TopicEventResponseStatus.success),
            StatusCode.OK,
            id="ok_status_code_for_success_response",
        ),
        pytest.param(
            TopicEventResponse(TopicEventResponseStatus.retry),
            StatusCode.ERROR,
            id="error_status_code_for_retry_response",
        ),
        pytest.param(
            TopicEventResponse(TopicEventResponseStatus.drop),
            StatusCode.ERROR,
            id="error_status_code_for_drop_response",
        ),
        pytest.param(
            None, StatusCode.UNSET, id="default_status_code_for_none_response"
        ),
    ],
)
def test_set_span_status_from_cloudevent_handler(
    response: TopicEventResponse | None, expected_span_status: StatusCode
) -> None:
    @set_span_status_from_cloudenvet_handler_result
    def cloudevent_handler(_: v1.Event) -> TopicEventResponse:
        return response

    with new_tracer().start_as_current_span(name="test_span") as span:
        _ = cloudevent_handler(v1.Event())
        assert span.status.status_code == expected_span_status


@pytest.mark.parametrize(
    ("event_extractor", "setup_cloudevent", "expected_span_event_data"),
    [
        pytest.param(
            lambda _: {"key1": "value1", "key2": "value2"},
            lambda: CloudEventBuilder().build(),
            {"key1": "value1", "key2": "value2"},
            id="uses custom event_extractor to return custom event payload",
        ),
        pytest.param(
            lambda _: {},
            lambda: CloudEventBuilder().build(),
            {},
            id="uses custom event_extractor to return empty event payload",
        ),
        pytest.param(
            extract_payload_from_cloudevent,
            lambda: (
                CloudEventBuilder()
                .with_type("test_type")
                .with_id("test_id")
                .with_data("test_data")
                .with_content_type("application/json")
                .with_source("test_source")
                .with_extension("ext1", "value1")
                .with_subject("test_subject")
                .build()
            ),
            {
                "event_data": "test_data",
                "event_data_type": "str",
                "event_type": "test_type",
                "event_id": "test_id",
                "event_content_type": "application/json",
                "event_source": "test_source",
                "event_extensions": '{"ext1": "value1"}',
                "event_subject": "test_subject",
            },
            id="uses extract_payload_from_cloudevent",
        ),
    ],
)
def test_set_span_event_from_event(
    event_extractor: Callable,
    setup_cloudevent: Callable,
    expected_span_event_data: dict,
) -> None:
    @set_span_event_from_event(
        name="test_set_span_event_from_event", event_extractor=event_extractor
    )
    def cloudevent_handler(_: v1.Event) -> None:
        return

    with new_tracer().start_as_current_span(name="test_span") as span:
        _ = cloudevent_handler(setup_cloudevent())
        assert len(span._events) == 1
        assert span._events[0].attributes == expected_span_event_data

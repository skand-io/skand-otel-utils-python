from typing import Callable

from cloudevents.sdk.event import v1
from dapr.clients.grpc._response import TopicEventResponse

CloudEventHandler = Callable[[v1.Event], TopicEventResponse]

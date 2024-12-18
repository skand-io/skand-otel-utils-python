# Skand Otel Utils Python

Python utilities for OpenTelemetry (OTel) instrumentation and implementation, tailored for seamless integration and enhanced observability in Skand's projects.

## Usage

This can enhance your CloudEvent handler with the OpenTelemetry utils

```python
from cloudevents.sdk.event import v1
from dapr.clients.grpc._response import TopicEventResponse
from dapr.ext.grpc import App
from skand_otel_utils import publishers
from skand_otel_utils.cloudevents.decorators import setup_distributed_trace_context, trace_span

app = App()


@app.subscribe(pubsub_name="YOUR_PUBSUB_NAME" ,topic="YOUR_TOPIC")
@setup_distributed_trace_context()
@trace_span.set_span_event_from_event(name="event payload", event_extractor=trace_span.extract_payload_from_cloudevent)
@trace_span.set_span_status_from_cloudenvet_handler_result
def handler(event: v1.Event) -> TopicEventResponse:
    pass

app.run()
```

## Installation from a Private GitHub Repository

### uv

#### Install the Package

To install a specific version of the package from the private repository:

```shell
uv add git+https://github.com/skand-io/skand-otel-utils-python.git.git --tag <tag_name>
```

Note: Ensure your GitHub account has access to the private repository.

#### Debug Installation Before Publishing

To debug the package installation, specify the filesystem path of the package:

```shell
uv add <relative_path_to_debugging_package>
```

### Poetry

For detailed instructions, refer to the [Poetry documentation on private repositories](https://python-poetry.org/docs/repositories/#private-repository-example).

#### Configure Access to GitHub Repositories for Poetry

```shell
poetry config repositories.skand-io-github-org https://github.com/skand-io/
poetry config http-basic.skand-io-github-org <username> <github_token>
```

Note: The GitHub token should have the permission to read the private repository.

#### Install the Package

To install a specific version of the package from the private repository:

```shell
poetry add "git+https://github.com/skand-io/skand-otel-utils-python.git#<tag_name>"
```

#### Debug Installation Before Publishing

To debug the package installation, specify the filesystem path of the package:

```shell
poetry add <relative_path_to_debugging_package>
```

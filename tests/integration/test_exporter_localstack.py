"""Integration tests for SigV4OTLPSpanExporter."""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer
import os
import pytest

from src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter import (
    SigV4OTLPSpanExporter,
)


@pytest.mark.integration
def test_export_to_localstack() -> None:
    """Test the SigV4OTLPSpanExporter with a localstack endpoint."""
    os.environ["AWS_ACCESS_KEY_ID"] = "test_access_key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test_secret_key"
    os.environ["AWS_REGION"] = "eu-central-1"

    exporter = SigV4OTLPSpanExporter(region="eu-central-1")

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("localstack-test-span") as span:
        span.set_attribute("localstack", "yes")

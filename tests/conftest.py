"""Test fixtures for the tests lol."""

from opentelemetry.sdk.trace import ReadableSpan
from pytest_mock import MockerFixture
import pytest

from src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter import (
    SigV4OTLPSpanExporter,
)


@pytest.fixture(scope="function")
def dummy_spans(mocker: MockerFixture) -> list[ReadableSpan]:
    """Return a list of mocked ReadableSpan instances."""
    dummy = mocker.Mock(spec=ReadableSpan)
    return [dummy for _ in range(5)]


@pytest.fixture(scope="function")
def exporter() -> SigV4OTLPSpanExporter:
    """Return a configured SigV4OTLPSpanExporter instance."""
    return SigV4OTLPSpanExporter(region="eu-central-1")


__all__ = ["dummy_spans", "exporter"]

"""SigV4 signed OTLP HTTP exporter."""

from src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter import (
    SigV4OTLPSpanExporter,
)

__all__ = ["SigV4OTLPSpanExporter"]

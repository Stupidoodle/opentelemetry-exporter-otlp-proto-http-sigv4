"""SigV4 HTTP Exporter for OpenTelemetry Protocol (OTLP)."""

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import ReadOnlyCredentials
from io import BytesIO
from os import environ
from time import sleep
from typing import Sequence
import boto3
import gzip
import logging
import requests
import zlib

from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_generator,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.proto.http import Compression, _OTLP_HTTP_HEADERS
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_logger = logging.getLogger(__name__)

MAX_UNCOMPRESSED_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SPANS_PER_BATCH = 10_000


class SigV4OTLPSpanExporter(SpanExporter):
    """OTLP exporter with AWS SigV4 requests signing, for X-Ray."""

    _MAX_RETRY_TIMEOUT = 64
    _region: str
    _endpoint: str
    _timeout: int
    _compression: Compression
    _headers: dict[str, str]
    _boto_session: boto3.Session
    _credentials: ReadOnlyCredentials
    _session: requests.Session
    _shutdown: bool

    def __init__(
        self,
        region: str = "eu-central-1",
        timeout: int = 10,
        compression: Compression | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the SigV4OTLPSpanExporter.

        Args:
            region: (str): The AWS region.
            timeout: (int): The timeout for the request.
            compression: (Compression): The compression type.
            headers: (dict[str, str]): Additional headers for the request.

        Returns:
            None

        """
        self._region = region
        self._endpoint = f"https://xray.{region}.amazonaws.com/v1/traces"
        self._timeout = timeout
        self._compression = compression or self._compression_from_env()
        self._headers = headers or {}

        self._boto_session = boto3.Session()
        self._credentials = (
            self._boto_session.get_credentials().get_frozen_credentials()
            # type: ignore
        )

        self._session = requests.Session()
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to the OTLP endpoint.

        Args:
            spans: (Sequence[ReadableSpan]): The spans to export.

        Returns:
            SpanExportResult: The result of the export operation.

        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring export")
            return SpanExportResult.FAILURE

        if len(spans) > MAX_SPANS_PER_BATCH:
            _logger.error(
                "Span batch contains %d spans (limit: %d)",
                len(spans),
                MAX_SPANS_PER_BATCH,
            )
            return SpanExportResult.FAILURE

        serialized_data = encode_spans(spans).SerializePartialToString()

        if len(serialized_data) > MAX_UNCOMPRESSED_BYTES:
            _logger.error(
                "Export failed: payload size %d " "exceeds 5MB uncompressed limit",
                len(serialized_data),
            )
            return SpanExportResult.FAILURE

        if self._compression == Compression.Gzip:
            buf = BytesIO()

            with gzip.GzipFile(fileobj=buf, mode="w") as f:
                f.write(serialized_data)

            serialized_data = buf.getvalue()
        elif self._compression == Compression.Deflate:
            serialized_data = zlib.compress(serialized_data)

        for delay in _create_exp_backoff_generator(max_value=self._MAX_RETRY_TIMEOUT):
            if delay == self._MAX_RETRY_TIMEOUT:
                return SpanExportResult.FAILURE

            resp = self._send(serialized_data)

            if resp.ok:
                return SpanExportResult.SUCCESS
            elif self._retryable(resp):
                _logger.warning(
                    "Transient error %s, retrying in %ss", resp.reason, delay
                )
                sleep(delay)
                continue
            else:
                _logger.error(
                    "Export failed - status: %s, response: %s",
                    resp.status_code,
                    resp.text,
                )
                return SpanExportResult.FAILURE

        return SpanExportResult.FAILURE

    def _send(self, data: bytes) -> requests.Response:
        """Send the data to the OTLP endpoint.

        Args:
            data: (bytes): The data to send.

        Returns:
            requests.Response: The response from the request.

        """
        headers = {
            "Content-Type": "application/x-protobuf",
            "Content-Length": str(len(data)),
            "Host": f"xray.{self._region}.amazonaws.com",
            **self._headers,
        }

        request = AWSRequest(
            method="POST",
            url=self._endpoint,
            data=data,
            headers=headers,
        )

        SigV4Auth(
            credentials=self._credentials,
            service_name="xray",
            region_name=self._region,
        ).add_auth(request=request)

        return self._session.post(
            url=self._endpoint,
            data=data,
            headers=dict(request.headers),
            timeout=self._timeout,
        )

    def shutdown(self) -> None:
        """Shutdown the exporter.

        Returns:
            None

        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring shutdown")
            return
        self._session.close()
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        """Check if the response is retryable.

        Args:
            resp: (requests.Response): The response to check.

        Returns:
            bool: True if the response is retryable, False otherwise.

        """
        return resp.status_code == 408 or 500 <= resp.status_code <= 599

    @staticmethod
    def _compression_from_env() -> Compression:
        """Get the compression type from the environment variables.

        Returns:
            Compression: The compression type.

        """
        env = (
            environ.get(
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
            )
            .lower()
            .strip()
        )

        return Compression(env)

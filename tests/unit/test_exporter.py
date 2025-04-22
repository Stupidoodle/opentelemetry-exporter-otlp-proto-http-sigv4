"""Unit tests for SigV4OTLPSpanExporter."""

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from pytest_mock import MockerFixture

from src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter import (
    MAX_SPANS_PER_BATCH,
    MAX_UNCOMPRESSED_BYTES,
    SigV4OTLPSpanExporter,
)


def test_export_success(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test successful export of spans.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )

    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    mocker.patch.object(exporter, "_send", return_value=mocker.Mock(ok=True))

    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.SUCCESS


def test_too_many_spans(
    mocker: MockerFixture, exporter: SigV4OTLPSpanExporter
) -> None:
    """Test export with too many spans.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.

    Returns:
        None

    """
    dummy = mocker.Mock(spec=ReadableSpan)
    dummy_spans = [dummy for _ in range(MAX_SPANS_PER_BATCH + 1)]

    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.FAILURE


def test_too_large_payload(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test export with too large payload.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )

    mock_encode.return_value.SerializePartialToString.return_value = b"x" * (
        MAX_UNCOMPRESSED_BYTES + 1
    )

    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.FAILURE


def test_retry_then_success(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test retry logic in export.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.sleep",
        return_value=None,
    )

    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    retry_resp = mocker.Mock(ok=False, status_code=500, reason="Internal Server Error")
    success_resp = mocker.Mock(ok=True)

    mock_send = mocker.patch.object(
        exporter, "_send", side_effect=[retry_resp, success_resp]
    )

    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.SUCCESS
    assert mock_send.call_count == 2


def test_non_retryable_error(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test non-retryable error in export.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    non_retryable_resp = mocker.Mock(ok=False, status_code=400, reason="Bad Request")

    mocker.patch.object(exporter, "_send", return_value=non_retryable_resp)

    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.FAILURE


def test_export_after_shutdown(
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test export after shutdown.

    Args:
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    exporter._shutdown = True
    result = exporter.export(dummy_spans)

    assert result == SpanExportResult.FAILURE


def test_force_flush_noop(
    exporter: SigV4OTLPSpanExporter,
) -> None:
    """Test force flush does nothing.

    Args:
        exporter: (SigV4OTLPSpanExporter): The exporter instance.

    Returns:
        None

    """
    result = exporter.force_flush()

    assert result is True


def test_shutdown_idempotent(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
) -> None:
    """Test shutdown is idempotent.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.

    Returns:
        None

    """
    mocker.patch.object(exporter._session, "close", autospec=True)

    exporter.shutdown()

    assert exporter._shutdown is True

    exporter.shutdown()  # Should not raise or log error


def test_export_with_gzip_compression(
    mocker: MockerFixture,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test export with gzip compression.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    exporter = SigV4OTLPSpanExporter(
        region="eu-central-1",
        compression=Compression.Gzip,
    )

    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    mocker.patch.object(exporter, "_send", return_value=mocker.Mock(ok=True))

    result = exporter.export(dummy_spans)
    assert result == SpanExportResult.SUCCESS


def test_export_with_deflate_compression(
    mocker: MockerFixture,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test export with deflate compression.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    exporter = SigV4OTLPSpanExporter(
        region="eu-central-1",
        compression=Compression.Deflate,
    )

    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    mocker.patch.object(exporter, "_send", return_value=mocker.Mock(ok=True))

    result = exporter.export(dummy_spans)
    assert result == SpanExportResult.SUCCESS


def test_retry_exhaustion_failure(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Test retry exhaustion failure.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter._create_exp_backoff_generator",
        return_value=[1] * (exporter._MAX_RETRY_TIMEOUT - 1)
        + [exporter._MAX_RETRY_TIMEOUT],
    )

    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.sleep",
        return_value=None,
    )

    mocker.patch.object(
        exporter,
        "_send",
        return_value=mocker.Mock(
            ok=False, status_code=500, reason="Internal Server Error"
        ),
    )

    result = exporter.export(dummy_spans)
    assert result == SpanExportResult.FAILURE


def test_send_executes_sigv4_request(
    mocker: MockerFixture,
) -> None:
    """Test that the send method executes a SigV4 request.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.

    Returns:
        None

    """
    exporter = SigV4OTLPSpanExporter(
        region="eu-central-1",
    )
    mock_post = mocker.patch.object(exporter._session, "post", autospec=True)

    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.SigV4Auth.add_auth"
    )

    response = exporter._send(b"test-data")

    mock_post.assert_called_once()
    assert response == mock_post.return_value


def test_retry_final_fallback_failure(
    mocker: MockerFixture,
    exporter: SigV4OTLPSpanExporter,
    dummy_spans: list[ReadableSpan],
) -> None:
    """Ensure export fails with retry loop exhausted but not reaching MAX_RETRY_TIMEOUT.

    Args:
        mocker: (MockerFixture): The pytest mocker fixture.
        exporter: (SigV4OTLPSpanExporter): The exporter instance.
        dummy_spans: (list[ReadableSpan]): The dummy spans to export.

    Returns:
        None

    """
    mock_encode = mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.encode_spans"
    )
    mock_encode.return_value.SerializePartialToString.return_value = b"valid-bytes"

    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter.sleep",
        return_value=None,
    )

    # Provide 3 retryable delays (not hitting MAX_RETRY_TIMEOUT)
    mocker.patch(
        "src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter._create_exp_backoff_generator",
        return_value=[1, 2, 3],  # No MAX_RETRY_TIMEOUT here
    )

    mocker.patch.object(
        exporter,
        "_send",
        return_value=mocker.Mock(ok=False, status_code=500, reason="server die"),
    )

    result = exporter.export(dummy_spans)
    assert result == SpanExportResult.FAILURE

# 🛰️ OpenTelemetry SigV4 OTLP Exporter for Python

[![Test & Lint](https://github.com/Stupidoodle/opentelemetry-exporter-otlp-proto-http-sigv4/actions/workflows/test.yml/badge.svg)](https://github.com/Stupidoodle/opentelemetry-exporter-otlp-proto-http-sigv4/actions/workflows/test.yml)
[![codecov](https://codecov.io/github/Stupidoodle/opentelemetry-exporter-otlp-proto-http-sigv4/branch/master/graph/badge.svg?token=6aVsspZtml)](https://codecov.io/github/Stupidoodle/opentelemetry-exporter-otlp-proto-http-sigv4)

An OTLP HTTP exporter for OpenTelemetry that supports **AWS SigV4 request signing**, designed for use in containerized Lambda environments or anywhere AWS X-Ray expects SigV4-authenticated telemetry data.

> 🛠️ The existing AWS Lambda OTLP Layer **does not work in containerized Lambda apps** — this exporter solves that.

---

## 🔧 Features

- Full SigV4 signing using `botocore`
- Supports gzip/deflate compression
- 100% compatible with AWS OTLP endpoint (`xray.<region>.amazonaws.com`)
- Graceful retry logic, exponential backoff
- Fully tested (unit + integration with LocalStack)

---

## 📦 Installation

```bash
pip install otel-sigv4-exporter
```

---

## 🧪 Quickstart

```python
from src.opentelemetry.exporter.otlp.proto.http.sigv4.exporter import SigV4OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

exporter = SigV4OTLPSpanExporter(region="eu-central-1")

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))
```

---

## 🧪 Tests

Run all tests including LocalStack-backed integration:

```bash
tox
```

To run inside Docker:

```bash
docker build -f tests/test.Dockerfile -t otlp-test .
docker run --rm --network=host otlp-test
```

---

## 🌐 Why This Exists

AWS only provides an [OTLP Lambda Layer](https://github.com/aws-observability/aws-otel-lambda/tree/main), which:

- ❌ doesn't work in containerized Lambda deployments
- ❌ doesn't support Python OTLP SDK directly
- ❌ requires extra sidecar setup

This exporter fills that gap.

---

## 📋 Roadmap

- [x] LocalStack-backed integration tests
- [x] Full CI with tox + pytest
- [x] GitHub Actions + Codecov
- [X] PyPI release (`otel-sigv4-exporter`)
- [ ] OpenTelemetry upstream discussion or PR

---

## 🧠 Credits

Built with love, caffeine, and psychological warfare.<br>
Brought to you by [@stupidoodle](https://github.com/stupidoodle)

---
FROM python:3.13.2-slim

WORKDIR /app

COPY pyproject.toml tox.ini ./
COPY src/ ./src/
COPY tests/ ./tests/

RUN pip install --upgrade pip && pip install tox

CMD ["tox", "-e", "integration"]
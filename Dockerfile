FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir . \
 && groupadd --system app \
 && useradd --system --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app

USER app:app

# Configuration verification only. No HTTP listener.
CMD ["yougile-mcp", "doctor"]

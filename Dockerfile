FROM python:3.15-slim AS build

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./
COPY src/ ./src/

RUN python -m pip install uv==0.13.8 \
 && uv sync --locked --no-dev --no-editable --extra cloud

FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app
COPY --from=build /app/.venv /app/.venv

RUN groupadd --system app \
 && useradd --system --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app

USER app:app

# Safe default: configuration verification only. Cloud mode requires
# explicit docker compose command and a private Docker network.
CMD ["yougile-mcp", "doctor"]

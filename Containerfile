# builder

FROM docker.io/astral/uv:python3.14-trixie AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,z \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,z \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN uv run python -m compileall -q /app

# runner

FROM docker.io/python:3.14-slim-trixie

RUN groupadd -r app && useradd -r -g app appuser
WORKDIR /app

# Data directory for the on-disc cache; mounted as a volume at runtime.
RUN mkdir -p /app/data && chown appuser:app /app/data

COPY --from=builder --chown=appuser:app /app/.venv /app/.venv

COPY --from=builder --chown=appuser:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

CMD ["python", "main.py"]

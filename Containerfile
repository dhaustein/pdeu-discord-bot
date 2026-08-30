# builder

FROM docker.io/astral/uv:python3.14-trixie AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

# --frozen: release-please bumps pyproject.toml version without regenerating
# uv.lock (version-only drift), so skip lock validation here.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . /app

RUN uv run python -m compileall -q /app

# runner

FROM docker.io/python:3.14-slim-trixie

# Fixed UID so runAsNonRoot is verifiable by Argocd
RUN groupadd -r -g 10000 app && useradd -r -u 10000 -g app appuser
WORKDIR /app

# Data directory for the on-disc cache; mounted as a volume at runtime.
RUN mkdir -p /app/data && chown appuser:app /app/data

COPY --from=builder --chown=appuser:app /app/.venv /app/.venv

COPY --from=builder --chown=appuser:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER 10000

CMD ["python", "main.py"]

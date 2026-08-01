FROM docker.io/astral/uv:python3.14-trixie AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# 1. Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# 2. Copy the application source code (flat project structure)
COPY . /app

# 3. Explicitly byte-compile the application code
# This will generate the optimized __pycache__ directories for all your .py files
RUN uv run python -m compileall -q /app


FROM docker.io/python:3.14-slim-trixie

RUN groupadd -r app && useradd -r -g app appuser
WORKDIR /app

# Copy the compiled virtual environment
COPY --from=builder --chown=appuser:app /app/.venv /app/.venv

# Copy the application code AND the newly generated __pycache__ directories
COPY --from=builder --chown=appuser:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

# Run the bot
CMD ["python", "main.py"]

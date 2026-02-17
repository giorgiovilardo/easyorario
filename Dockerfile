FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app /app

VOLUME /app/data

ENV DATABASE_URL=sqlite+aiosqlite:///data/app.db
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["litestar", "--app", "easyorario.app:app", "run", "--host", "0.0.0.0", "--port", "8000"]

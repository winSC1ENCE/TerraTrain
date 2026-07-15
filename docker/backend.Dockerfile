FROM python:3.12-slim AS builder

RUN pip install uv

WORKDIR /build
COPY apps/backend/pyproject.toml apps/backend/
COPY pyproject.toml ./
RUN uv sync --project apps/backend --no-dev --no-install-project

COPY apps/backend/src apps/backend/src
RUN uv sync --project apps/backend --no-dev


FROM python:3.12-slim AS runtime

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /build/apps/backend/src ./src
RUN chown -R app:app /app

USER app
EXPOSE 8000

CMD ["uvicorn", "terratrain.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


FROM runtime AS development

USER root
COPY --from=builder /build/.venv /app/.venv
USER app

CMD ["uvicorn", "terratrain.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

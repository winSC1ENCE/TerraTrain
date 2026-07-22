FROM python:3.12-slim AS builder

RUN pip install uv

# Build the venv at the SAME path it will live at runtime so console-script
# shebangs (e.g. uvicorn) point at an interpreter that exists in the final image.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

COPY pyproject.toml ./
COPY apps/backend/pyproject.toml apps/backend/pyproject.toml
# Install third-party dependencies only; the app source is delivered via PYTHONPATH.
RUN uv sync --project apps/backend --no-dev --no-install-project


FROM python:3.12-slim AS runtime

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv /app/.venv
COPY apps/backend/src ./src
RUN chown -R app:app /app

USER app
EXPOSE 8000

CMD ["uvicorn", "terratrain.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


FROM runtime AS development

CMD ["uvicorn", "terratrain.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

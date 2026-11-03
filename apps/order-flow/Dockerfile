FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY migrations ./migrations
COPY alembic.ini ./
COPY schemas ./schemas

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

CMD ["uvicorn", "order_flow.api:app", "--host", "0.0.0.0", "--port", "8000"]

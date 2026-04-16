FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source first — pip install needs the app package present
COPY api/pyproject.toml .
COPY api/app/ app/
RUN pip install --no-cache-dir .

COPY api/alembic.ini .
COPY api/alembic/ alembic/

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /service

# Shared utilities (correlation, logging)
COPY shared/ /service/shared/

# Service code
COPY services/decision-hub/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/decision-hub/ .

ENV PYTHONPATH=/service
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run migrations then start the service
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002"]

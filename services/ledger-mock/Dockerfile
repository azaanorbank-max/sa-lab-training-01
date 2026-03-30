FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY shared/ /service/shared/

COPY services/ledger-mock/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ledger-mock/ .

ENV PYTHONPATH=/service
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8003"]

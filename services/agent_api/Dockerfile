FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY pytest.ini .
COPY eval_data ./eval_data

RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_DB_PATH=/data/app.sqlite \
    MODEL_PROVIDER=simulator

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

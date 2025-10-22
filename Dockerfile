FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "uvicorn[standard]"


COPY . .

EXPOSE 8000

CMD ["python", "main.py"]

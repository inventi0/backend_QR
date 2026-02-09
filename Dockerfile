# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.12-slim-bookworm AS builder

# Установка build зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка Python зависимостей ГЛОБАЛЬНО (не --user)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "uvicorn[standard]"

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim-bookworm

# Установка runtime зависимостей (только curl для healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование установленных пакетов из builder (глобальные site-packages)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование кода приложения
COPY . .

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ping || exit 1

CMD ["python", "main.py"]

"""
Rate Limiting Configuration

Защита от брутфорса и DDoS атак.
"""
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# Limiter с ключом по IP адресу
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],  # дефолтный лимит: 200 запросов в минуту
)

# Специальные лимиты для критичных эндпоинтов
AUTH_RATE_LIMIT = "5 per minute"      # Логин/регистрация: 5 попыток в минуту
UPLOAD_RATE_LIMIT = "10 per minute"   # Загрузка файлов: 10 в минуту
API_RATE_LIMIT = "100 per minute"     # API запросы: 100 в минуту

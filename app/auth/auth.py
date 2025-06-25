from fastapi_users.authentication import BearerTransport, AuthenticationBackend, JWTStrategy
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Bearer-транспорт
bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

# Получение секретного ключа из переменной окружения
private_key = os.getenv('private_key')

# Функция для создания JWT-стратегии
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=private_key, lifetime_seconds=3600)

# Конфигурация аутентификации
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
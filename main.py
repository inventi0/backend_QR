from fastapi import FastAPI
import uvicorn
from app import models
import database
from app.routes import router  # Импортируем роуты из routes.py

# Инициализация приложения FastAPI
app = FastAPI()

# Создание всех таблиц в базе данных
database.Base.metadata.create_all(bind=database.engine)

# Подключение всех роутов
app.include_router(router)  # Включаем все роуты из routes.py

@app.get("/")
def read_root():
    return {"msg": "Hello from FastAPI + Postgres!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

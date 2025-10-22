import uvicorn
from app.routes.user import app as fastapi_app

if __name__ == "__main__":
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        workers=1
    )
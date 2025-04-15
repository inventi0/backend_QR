from fastapi import FastAPI
import uvicorn
from fastapi import FastAPI
from database import Base, engine
from app import models
from sqlalchemy import create_engine
app = FastAPI()

Base.metadata.create_all(bind=engine)
from sqlalchemy import create_engine
sync_engine = create_engine("postgresql://myuser:mypassword@db:5432/mydatabase")
Base.metadata.create_all(bind=sync_engine)
@app.get("/")
def read_root():
    return {"msg": "Hello from FastAPI + Postgres!"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)




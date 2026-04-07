from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    db_url = os.getenv("DATABASE_URL")
    return {
        "status": "Laboratorio online",
        "tfg": "Seguridad en APIs GaaS",
        "database_config": "conectada" if db_url else "Error de config"
    }

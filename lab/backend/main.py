from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models
from database import engine, get_db

#crear las tablas
models.Base.metadata.create_all(bind=engine)
app = FastAPI()
@app.get("/")
def read_root():
    return {"status": "Laboratorio Online", "db_status": "Tablas Creadas/Verificadas"}
#endpoint de prueba para ver el inventario de alguien
@app.get("/inventory/{user_id}")
def get_inventory(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    return {"user": user.username, "inventory": user.items}

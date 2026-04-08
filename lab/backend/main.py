from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import engine, get_db

#genera las tablas fisicas en postgres si no existen
models.Base.metadata.create_all(bind=engine)
app = FastAPI()
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    #para registrar un usuario nuevo en el laboratorio
    db_user = models.User(steam_id=user.steam_id, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/inventory/{user_id}/items/", response_model=schemas.Inventory)
def add_item_to_user(user_id: int, item: schemas.InventoryCreate, db: Session = Depends(get_db)):
    #para asignar un objeto a un jugador especifico
    db_item = models.Inventory(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/inventory/{user_id}", response_model=List[schemas.Inventory])
def get_inventory(user_id: int, db: Session = Depends(get_db)):
    #endpoint vulnerable a bola: falta verificar si el token coincide con user_id
    items = db.query(models.Inventory).filter(models.Inventory.owner_id == user_id).all()
    return items

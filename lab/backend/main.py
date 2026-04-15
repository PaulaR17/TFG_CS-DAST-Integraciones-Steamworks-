import httpx #libreria para que la api hable con steam
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, database
import uuid #para los ids profesionales tipo uuid

#crea las tablas con el formato uuid para evitar ids predecibles 
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

#simulamos la respuesta de valve 
async def verify_steam_identity(ticket: str):
    if len(ticket) < 10:
        raise HTTPException(status_code=401, detail="ticket invalido")
    return {"steam_id": "76561198000000001", "username": "Paula_Pro"}

@app.post("/auth/login")
async def login(ticket: str, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.steam_id == ticket).first()
    
    if not user:
        user = models.User(steam_id=ticket, username=f"Jugador_{ticket}")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return {"status": "login exitoso", "user_id": str(user.id)}


@app.post("/inventory/{user_id}/items")
def add_item(user_id: uuid.UUID, item: schemas.InventoryCreate, db: Session = Depends(database.get_db)):
    #añadimos objetos a la mochila de un id especifico
    db_item = models.Inventory(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/inventory/{user_id}")
def get_inventory(user_id: uuid.UUID, db: Session = Depends(database.get_db)):
    # Un atacante puede cambiar el id en la url y robar datos de otros
    return db.query(models.Inventory).filter(models.Inventory.owner_id == user_id).all()


@app.get("/users/{user_id}")
def get_user_profile(user_id: uuid.UUID, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "username": user.username,
        "credits": user.credits,
        "is_admin": user.is_admin
    }
import httpx #libreria para que la api hable con steam
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, database
import uuid #para los ids profesionales tipo uuid

#crea las tablas con el formato uuid para evitar ids predecibles [cite: 39]
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

#simulamos la respuesta de valve segun tu tfg [cite: 50, 86]
async def verify_steam_identity(ticket: str):
    if len(ticket) < 10:
        raise HTTPException(status_code=401, detail="ticket invalido")
    return {"steam_id": "76561198000000001", "username": "Paula_Pro"}

@app.post("/auth/login")
async def login(ticket: str, db: Session = Depends(database.get_db)):
    steam_user = await verify_steam_identity(ticket)
    user = db.query(models.User).filter(models.User.steam_id == steam_user["steam_id"]).first()
    
    if not user:
        user = models.User(steam_id=steam_user["steam_id"], username=steam_user["username"])
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return {"status": "login exitoso", "user_id": str(user.id)}

# --- ENDPOINTS DE INVENTARIO (Los que te faltaban) ---

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
    # VULNERABILIDAD BOLA: No comprobamos si el que pide es el dueño [cite: 38, 51]
    # Un atacante puede cambiar el id en la url y robar datos de otros [cite: 39, 41]
    return db.query(models.Inventory).filter(models.Inventory.owner_id == user_id).all()

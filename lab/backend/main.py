from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import models
import schemas
import database
from security import create_demo_token, get_current_identity
from audit_logger import write_audit_log
import base64
import json

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Steamworks DAST Lab API",
    description="Laboratorio vulnerable para auditoría DAST stateful sobre flujos tipo Steamworks.",
    version="1.0.0"
)

#simulacion muy simple de steamworks

async def verify_steam_identity(steam_ticket: str):
    """
    simula la validacion de un ticket de steam.
    aqui solo miro si el ticket existe en este diccionario de prueba.
    """

    demo_users = {
        "STEAM_TICKET_PAULA": {
            "steam_id": "76561198000000001",
            "username": "Paula_Pro"
        },
        "STEAM_TICKET_ATTACKER": {
            "steam_id": "76561198000000002",
            "username": "Attacker_Test"
        },
        "STEAM_TICKET_VICTIM": {
            "steam_id": "76561198000000003",
            "username": "Victim_Test"
        }
    }

    if steam_ticket not in demo_users:
        raise HTTPException(status_code=401, detail="Invalid Steam ticket")

    return demo_users[steam_ticket]


@app.get("/")
def root():
    return {
        "status": "running",
        "project": "Steamworks DAST Lab",
        "docs": "/docs"
    }


#auth

@app.post("/auth/steam_login")
def steam_login(
    payload: schemas.SteamLoginRequest,
    db: Session = Depends(database.get_db)
):
    """
    Login específico para clientes Steamworks.
    En un entorno Steamworks real, validaríamos el ticket contra Steam Web API.
    En este laboratorio, aceptamos el SteamID como prueba de identidad.
    """
    # Buscar usuario existente por steam_id (almacenado en username con prefijo steam_)
    steam_username = f"steam_{payload.steam_id}"
    user = db.query(models.User).filter(models.User.username == steam_username).first()

    if not user:
        # Auto-registro al primer login con Steam (típico en GaaS)
        user = models.User(
            steam_id=payload.steam_id,
            username=steam_username,
            credits=100,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        write_audit_log("steam_user_registered", {
            "steam_id": payload.steam_id,
            "persona_name": payload.persona_name,
            "user_id": str(user.id)
        })

    # Genero el mismo tipo de token débil que el login normal
    # (mantenemos la vulnerabilidad intencional en weak token para que sea auditable)
    token_payload = {"user_id": str(user.id), "username": user.username}
    access_token = base64.urlsafe_b64encode(
        json.dumps(token_payload).encode()
    ).decode()

    write_audit_log("steam_login", {
        "steam_id": payload.steam_id,
        "persona_name": payload.persona_name,
        "user_id": str(user.id)
    })

    return {
        "access_token": access_token,
        "user_id": str(user.id),
        "username": user.username,
        "credits": user.credits
    }


#usuarios

@app.get("/users/me", response_model=schemas.UserOut)
def get_me(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #saco el usuario actual usando el user_id que viene dentro del token
    user = db.query(models.User).filter(
        models.User.id == uuid.UUID(identity["user_id"])
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/vulnerable/users/me", response_model=schemas.UserOut)
def vulnerable_update_me(
    update: schemas.VulnerableUserUpdate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(
        models.User.id == uuid.UUID(identity["user_id"])
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = update.model_dump(exclude_unset=True)

    #vulnerabilidad intencionada: aplico cualquier campo que venga en el json
    #por eso si el cliente manda credits o is_admin, tambien se intenta guardar
    for field, value in data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    write_audit_log("vulnerable_profile_update", {
        "user_id": str(user.id),
        "received_fields": list(data.keys())
    })

    return user


@app.patch("/secure/users/me", response_model=schemas.UserOut)
def secure_update_me(
    update: schemas.SafeUserUpdate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(
        models.User.id == uuid.UUID(identity["user_id"])
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = update.model_dump(exclude_unset=True)

    #version segura: aunque lleguen mas campos, solo acepto cambiar username
    if "username" in data:
        setattr(user, "username", data["username"])

    db.commit()
    db.refresh(user)

    write_audit_log("secure_profile_update", {
        "user_id": str(user.id),
        "received_fields": list(data.keys())
    })

    return user


#inventario

@app.post("/inventory/me/items", response_model=schemas.InventoryOut)
def add_my_item(
    item: schemas.InventoryCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #creo un item y lo ato al usuario autenticado, no a un id que venga del cliente
    db_item = models.Inventory(
        item_name=item.item_name,
        quantity=item.quantity,
        owner_id=uuid.UUID(identity["user_id"])
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    write_audit_log("add_inventory_item", {
        "user_id": identity["user_id"],
        "item_name": item.item_name,
        "quantity": item.quantity
    })

    return db_item


@app.get("/vulnerable/inventory/{user_id}", response_model=list[schemas.InventoryOut])
def vulnerable_get_inventory(
    user_id: uuid.UUID,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #vulnerabilidad intencionada: leo el user_id de la url sin compararlo con el token
    #asi un atacante puede pedir el inventario de otra persona si conoce su id
    items = db.query(models.Inventory).filter(
        models.Inventory.owner_id == user_id
    ).all()

    write_audit_log("vulnerable_inventory_access", {
        "authenticated_user_id": identity["user_id"],
        "requested_user_id": str(user_id),
        "items_returned": len(items)
    })

    return items


@app.get("/secure/inventory/{user_id}", response_model=list[schemas.InventoryOut])
def secure_get_inventory(
    user_id: uuid.UUID,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    authenticated_user_id = uuid.UUID(identity["user_id"])

    if user_id != authenticated_user_id:
        #si el id de la url no coincide con el del token, es un intento cruzado
        write_audit_log("blocked_bola_attempt", {
            "authenticated_user_id": str(authenticated_user_id),
            "requested_user_id": str(user_id)
        })
        raise HTTPException(status_code=403, detail="Forbidden")

    return db.query(models.Inventory).filter(
        models.Inventory.owner_id == authenticated_user_id
    ).all()


#logros

@app.post("/achievements/unlock", response_model=schemas.AchievementOut)
def unlock_achievement(
    achievement: schemas.AchievementCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #creo un logro para el usuario autenticado
    db_achievement = models.Achievement(
        achievement_code=achievement.achievement_code,
        unlocked=True,
        owner_id=uuid.UUID(identity["user_id"])
    )

    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)

    write_audit_log("achievement_unlocked", {
        "user_id": identity["user_id"],
        "achievement_code": achievement.achievement_code
    })

    return db_achievement


@app.get("/achievements/me", response_model=list[schemas.AchievementOut])
def get_my_achievements(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #devuelvo solo los logros del usuario que viene en el token
    return db.query(models.Achievement).filter(
        models.Achievement.owner_id == uuid.UUID(identity["user_id"])
    ).all()


#guardados en la nube

@app.post("/cloud/save", response_model=schemas.CloudSaveOut)
def create_cloud_save(
    save: schemas.CloudSaveCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #guardo una partida y la asocio al usuario autenticado
    db_save = models.CloudSave(
        slot_name=save.slot_name,
        save_data=save.save_data,
        owner_id=uuid.UUID(identity["user_id"])
    )

    db.add(db_save)
    db.commit()
    db.refresh(db_save)

    write_audit_log("cloud_save_created", {
        "user_id": identity["user_id"],
        "slot_name": save.slot_name
    })

    return db_save


@app.get("/cloud/saves/me", response_model=list[schemas.CloudSaveOut])
def get_my_cloud_saves(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #devuelvo solo los guardados del usuario actual
    return db.query(models.CloudSave).filter(
        models.CloudSave.owner_id == uuid.UUID(identity["user_id"])
    ).all()


#microtransacciones

@app.post("/transactions/init", response_model=schemas.TransactionOut)
def init_transaction(
    transaction: schemas.TransactionInit,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    #creo una transaccion pendiente para el usuario autenticado
    db_transaction = models.Transaction(
        order_id=transaction.order_id,
        item_name=transaction.item_name,
        amount=transaction.amount,
        owner_id=uuid.UUID(identity["user_id"])
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    write_audit_log("transaction_initialized", {
        "user_id": identity["user_id"],
        "order_id": transaction.order_id,
        "amount": transaction.amount
    })

    return db_transaction


@app.post("/vulnerable/transactions/finalize", response_model=schemas.TransactionOut)
def vulnerable_finalize_transaction(
    transaction: schemas.TransactionFinalize,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    db_transaction = db.query(models.Transaction).filter(
        models.Transaction.order_id == transaction.order_id
    ).first()

    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    #vulnerabilidad intencionada: me fio de approved_by_client
    #esto esta mal porque el cliente no deberia aprobar su propio pago
    if transaction.approved_by_client:
        setattr(db_transaction, "finalized", True)

        user = db.query(models.User).filter(
            models.User.id == uuid.UUID(identity["user_id"])
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        #sumo los creditos como si el pago hubiera sido real
        current_credits = int(getattr(user, "credits"))
        transaction_amount = int(getattr(db_transaction, "amount"))

        setattr(user, "credits", current_credits + transaction_amount)

    db.commit()
    db.refresh(db_transaction)

    write_audit_log("vulnerable_transaction_finalize", {
        "authenticated_user_id": identity["user_id"],
        "order_id": transaction.order_id,
        "approved_by_client": transaction.approved_by_client,
        "finalized": bool(getattr(db_transaction, "finalized"))
    })

    return db_transaction


@app.post("/secure/transactions/finalize", response_model=schemas.TransactionOut)
def secure_finalize_transaction(
    transaction: schemas.TransactionFinalize,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(database.get_db)
):
    db_transaction = db.query(models.Transaction).filter(
        models.Transaction.order_id == transaction.order_id,
        models.Transaction.owner_id == uuid.UUID(identity["user_id"])
    ).first()

    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    #version segura: no me fio del campo approved_by_client
    #en un caso real aqui se verificaria con steam web api o valve
    setattr(db_transaction, "finalized", False)

    db.commit()
    db.refresh(db_transaction)

    write_audit_log("secure_transaction_finalize_blocked", {
        "authenticated_user_id": identity["user_id"],
        "order_id": transaction.order_id,
        "reason": "client approval is not trusted"
    })

    raise HTTPException(
        status_code=403,
        detail="Transaction must be verified by Steam Web API"
    )

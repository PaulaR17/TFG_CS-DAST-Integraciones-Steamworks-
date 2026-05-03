from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


#auth: lo que entra y sale al hacer login

class LoginRequest(BaseModel):
    steam_ticket: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    steam_id: str
    username: str


#inventario: crear items y devolverlos por api

class InventoryCreate(BaseModel):
    item_name: str
    quantity: int = 1


class InventoryOut(BaseModel):
    id: UUID
    item_name: str
    quantity: int
    owner_id: UUID

    class Config:
        from_attributes = True


#perfil de usuario

class VulnerableUserUpdate(BaseModel):
    #este schema deja pasar campos sensibles para poder demostrar mass assignment
    username: Optional[str] = None
    credits: Optional[int] = None
    is_admin: Optional[bool] = None
    role: Optional[str] = None


class SafeUserUpdate(BaseModel):
    #este es el schema seguro: solo deja cambiar username
    username: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    steam_id: str
    username: str
    credits: int
    is_admin: bool

    class Config:
        from_attributes = True


#logros

class AchievementCreate(BaseModel):
    achievement_code: str


class AchievementOut(BaseModel):
    id: UUID
    achievement_code: str
    unlocked: bool
    owner_id: UUID

    class Config:
        from_attributes = True


#guardados en la nube

class CloudSaveCreate(BaseModel):
    slot_name: str
    save_data: str


class CloudSaveOut(BaseModel):
    id: UUID
    slot_name: str
    save_data: str
    owner_id: UUID

    class Config:
        from_attributes = True


#microtransacciones

class TransactionInit(BaseModel):
    order_id: str
    item_name: str
    amount: int


class TransactionFinalize(BaseModel):
    #este campo es peligroso porque el cliente no deberia decidir si pago o no
    order_id: str
    approved_by_client: bool = False


class TransactionOut(BaseModel):
    id: UUID
    order_id: str
    item_name: str
    amount: int
    approved_by_client: bool
    finalized: bool
    owner_id: UUID

    class Config:
        from_attributes = True

# --- Steam auth schemas ---

class SteamLoginRequest(BaseModel):
    steam_id: str
    persona_name: str
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID 

#campos base de los items
class InventoryBase(BaseModel):
    item_name: str
    quantity: int

class InventoryCreate(InventoryBase):
    pass

class Inventory(InventoryBase):
    id: UUID 
    owner_id: UUID 
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    steam_id: str
    username: str
    credits: Optional[int] = 100
    is_admin: Optional[bool] = False

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID 
    items: List[Inventory] = []
    class Config:
        from_attributes = True

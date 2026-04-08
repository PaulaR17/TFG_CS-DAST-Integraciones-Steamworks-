from pydantic import BaseModel
from typing import List, Optional

#campos base que comparten todos los objetos del inventario
class InventoryBase(BaseModel):
    item_name: str #nombre del objeto para el catalogo
    quantity: int #unidades que posee el jugador

#modelo para la creacion de objetos (el cliente no envia el id)
class InventoryCreate(InventoryBase):
    pass

#modelo completo que incluye datos de la base de datos
class Inventory(InventoryBase):
    id: int #identificador unico en la tabla
    owner_id: int #relacion con el usuario dueño
    class Config:
        from_attributes = True #para que pydantic lea modelos de sqlalchemy

#campos base de la identidad del jugador
class UserBase(BaseModel):
    steam_id: str #identificador unico de la plataforma steam
    username: str #alias del jugador en el juego

#modelo para registrar nuevos usuarios
class UserCreate(UserBase):
    pass

#modelo de usuario que incluye su lista de items
class User(UserBase):
    id: int 
    items: List[Inventory] = [] #lista vinculada por owner_id
    class Config:
        from_attributes = True

from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from database import Base


#tabla principal de usuarios del lab
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    credits = Column(Integer, default=100)
    is_admin = Column(Boolean, default=False)

    #relaciones para poder navegar desde un usuario a sus cosas
    items = relationship("Inventory", back_populates="owner")
    achievements = relationship("Achievement", back_populates="owner")
    cloud_saves = relationship("CloudSave", back_populates="owner")
    transactions = relationship("Transaction", back_populates="owner")


#cada fila es un item del inventario y siempre pertenece a un usuario
class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="items")


#logros desbloqueados por cada usuario
class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    achievement_code = Column(String, nullable=False)
    unlocked = Column(Boolean, default=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="achievements")


#partidas guardadas en la nube, tambien asociadas a un usuario
class CloudSave(Base):
    __tablename__ = "cloud_saves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_name = Column(String, nullable=False)
    save_data = Column(Text, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="cloud_saves")


#transacciones de compra; en el lab sirven para probar el fallo de pagos
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    approved_by_client = Column(Boolean, default=False)
    finalized = Column(Boolean, default=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="transactions")

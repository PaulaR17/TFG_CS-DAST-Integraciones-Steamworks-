from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

#cojo la url de la base de datos desde docker-compose
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


#creo una sesion de base de datos para cada peticion y la cierro al acabar
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

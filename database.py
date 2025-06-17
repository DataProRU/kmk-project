import os

from fastapi import APIRouter, Request, Depends
from sqlalchemy import Column, Integer, String, Date, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Строка подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Создаем базовый класс для моделей
Base = declarative_base()

# Определение модели WebUser с использованием SQLAlchemy
class WebUser(Base):
    __tablename__ = "web_users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, server_default="user")

class New_Reports(Base):
    __tablename__ = "new_reports"
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    username = Column(String(255))
    tg_username = Column(String(255))
    accounting_type = Column(String(255))
    check_photo = Column(String(255))
    comment = Column(Text)

class Users(Base):
    __tablename__ = "tg_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    tg_username = Column(String(255))

class Payments(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_now = Column(DateTime)
    username = Column(String(255))
    date = Column(Date)
    contact_number = Column(String(255))
    accounting_type = Column(String(255))
    payment_type = Column(String(255))
    check_photo = Column(String(255))
    comment = Column(Text)

class New_registrations(Base):
    __tablename__ = "new_registrations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_now = Column(DateTime)
    username = Column(String(255))
    fullname = Column(String(255))
    phone = Column(String(255))
    city = Column(String(255))
    activity_type = Column(String(255))
    contacts_link = Column(String(255))

class Metrics(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))

class Accounting_types(Base):
    __tablename__ = "accounting_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))

class Payment_types(Base):
    __tablename__ = "payment_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))

class Activity_types(Base):
    __tablename__ = "activity_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))

# Асинхронная функция для создания таблиц
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        yield session

# Example route to test the database connection
@router.get("/")
async def read_root(db: AsyncSession = Depends(get_db)):
    return {"message": "Database connection is working"}

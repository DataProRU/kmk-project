import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, WebAppInfo
from aiogram.filters import Command
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, select
from dotenv import load_dotenv

load_dotenv()

# Конфигурация бота и базы данных
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка базы данных
async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Модель пользователя
class Users(Base):
    __tablename__ = "tg_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    tg_username = Column(String(255))


# URL для веб-приложений
MA_URL_REPORT = os.getenv("MA_URL_REPORT")
MA_URL_PAYMENT = os.getenv("MA_URL_PAYMENT")


def say_time(hour):
    """Определяет приветствие по времени суток"""
    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 24:
        return "Добрый вечер"
    elif 0 <= hour < 6:
        return "Доброй ночи"


def start_keyboard_gen(username: str, full_name: str):
    """Создает клавиатуру с кнопками для отчетов и платежей"""
    report_url = f"{MA_URL_REPORT}/{username}?username={full_name}"
    payment_url = f"{MA_URL_PAYMENT}?username={full_name}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Внести отчёт", web_app=WebAppInfo(url=report_url))],
        [InlineKeyboardButton(text="Внести чек", web_app=WebAppInfo(url=payment_url))]
    ])
    return keyboard


async def get_user_by_tg_username(session: AsyncSession, tg_username: str):
    """Проверяет наличие пользователя в базе данных"""
    query = select(Users).where(Users.tg_username == tg_username)
    result = await session.execute(query)
    user = result.scalar()
    return user


@dp.message(Command("start"))
async def start_command(message: Message):
    """Обрабатывает команду /start"""
    tg_username = f"{message.from_user.username}"  # Никнейм пользователя в Telegram
    user_id = message.from_user.id

    async with async_session() as session:
        user = await get_user_by_tg_username(session, tg_username)

    if user:
        current_datetime = datetime.now().replace(microsecond=0)
        hour = current_datetime.hour
        greeting = say_time(hour)
        await bot.send_message(
            user_id,
            f"{greeting}, {user.username}\nВнесите отчёт!",
            reply_markup=start_keyboard_gen(user.tg_username, user.username)
        )
    else:
        await bot.send_message(
            user_id,
            "У вас нет доступа к данному боту. Пожалуйста, обратитесь к администратору."
        )


async def main():
    """Запуск бота"""
    print("Бот запущен и готов к работе")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

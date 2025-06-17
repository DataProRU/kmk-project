import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Укажите ваш токен от BotFather
BOT_TOKEN = os.getenv("REGISTER_BOT_TOKEN")

# Настройка базы данных
DATABASE_URL = os.getenv("DATABASE_URL")
async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# URL мини-приложения
WEB_APP_URL = os.getenv("WEB_APP_URL")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

welcome_message = """
Мы создали профессиональное сообщество, где мы как эксперты в своих областях:
- Обмениваемся опытом
- Объединяемся в команды
- Находим клиентов

Пожалуйста, заполните анкету, нажав кнопку ниже. 
Ваши ответы помогут нам лучше понять вашу экспертность, классифицировать вашу деятельность для создания условий эффективного взаимодействия
"""


@dp.message(Command("start"))
async def start_command_handler(message: types.Message):
    # Получаем ник пользователя
    tg_username = message.from_user.username
    user_id = message.from_user.id

    web_app_url_with_params = f"{WEB_APP_URL}?username={tg_username}&user_id={user_id}"

    # Создаем инлайн-клавиатуру с кнопкой для мини-приложения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заполнить анкету", web_app=WebAppInfo(url=web_app_url_with_params))]
    ])

    # Отправляем приветственное сообщение с кнопкой, если пользователь не гость
    await bot.send_message(
        user_id,
        welcome_message,
        reply_markup=keyboard
    )


async def send_video_with_button(user_id: str):
    # Путь к видеофайлу
    video_path = "static/video/video.mp4"
    
    # Создаем инлайн-клавиатуру с кнопкой для вступления в канал
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вступить в канал", url=os.getenv("TG_GROUP_URL"))]
    ])
    
    # Используем FSInputFile для загрузки видео из локальной файловой системы
    video_file = FSInputFile(video_path)
    
    # Отправляем video note с инлайн-кнопкой
    await bot.send_video_note(
        chat_id=user_id,
        video_note=video_file,  # Передаем объект FSInputFile
        reply_markup=keyboard
    )


async def main():
    # Запуск бота
    print("Starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

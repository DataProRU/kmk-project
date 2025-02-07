import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Укажите ваш токен от BotFather
BOT_TOKEN = "7541267383:AAFgtWCq6g11XyY4RiecVJlvPst3k7TmlBE"

# Настройка базы данных
DATABASE_URL = "postgresql+asyncpg://db_admin:Hrat6ZyQJORU@37.143.10.252/kmk_mebel"
async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# URL мини-приложения
# WEB_APP_URL = "https://garage-garageshop.amvera.io/register_bot_add"
WEB_APP_URL = "http://127.0.0.1:8000/register_bot_add"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_command_handler(message: types.Message):
    # Получаем ник пользователя
    tg_username = message.from_user.username
    user_id = message.from_user.id

    web_app_url_with_params = f"{WEB_APP_URL}?username={tg_username}"
    # print(f"Web App URL: {web_app_url_with_params}")  # Логирование для проверки

    # Создаем инлайн-клавиатуру с кнопкой для мини-приложения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Заполнить анкету",web_app=WebAppInfo(url=web_app_url_with_params))]
    ])

    # Отправляем приветственное сообщение с кнопкой, если пользователь не гость
    await bot.send_message(
        user_id,
        f"Текст по дальнейшим шагам для пользователя (позже скину)",
        reply_markup=keyboard
    )


async def main():
    # Запуск бота
    print("Starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

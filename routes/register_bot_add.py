import os

from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db, Activity_types, New_registrations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import gspread
from datetime import datetime
import pytz

from register_bot import send_video_with_button
from dotenv import load_dotenv

load_dotenv()


router = APIRouter()
templates = Jinja2Templates(directory="templates/register_bot")

gc = gspread.service_account(filename=os.getenv("GOOGLE_TABLES_CREDENTIALS_FILE"))
sht2 = gc.open_by_url(os.getenv("GOOGLE_TABLES_REGISTER_BOT_URL"))
worksheet_registration = sht2.get_worksheet(0)

moscow_tz = pytz.timezone('Europe/Moscow')

@router.get("/register_bot_add", response_class=HTMLResponse)
async def read_register_form(request: Request, username: str,  user_id: str, db: AsyncSession = Depends(get_db), ):
    stmt = select(Activity_types)
    result = await db.execute(stmt)
    activity_types = result.scalars().all()
    return templates.TemplateResponse("form.html", {"request": request,
                                                    "username": username,
                                                    "user_id": user_id,
                                                    "activity_types": activity_types})


@router.post("/send_registration")
async def submit(
    username: str = Form(),
    user_id: str = Form(),
    fullname: str = Form(),
    phone: str = Form(),
    city: str = Form(),
    activity_type: str = Form(),
    contacts_link: str = Form(),
    db: AsyncSession = Depends(get_db),
):

    username = username.replace("%20", " ")
    await send_video_with_button(user_id)

    phone = ''.join(e for e in phone if e.isdigit())

    # Добавление записи в Google Таблицу
    worksheet_registration.format('A:A', {  # Форматирование столбца с датами
        "numberFormat": {
            "type": "DATE",
            "pattern": "dd.mm.yyyy"
        }
    })

    current_time = datetime.now(moscow_tz)
    formatted_time = current_time.strftime("%d-%m-%Y")
    naive_current_time = current_time.replace(tzinfo=None)

    new_row = [
        formatted_time,
        username,
        fullname,
        phone,
        city,
        activity_type,
        contacts_link,
    ]
    worksheet_registration.append_row(new_row, value_input_option="USER_ENTERED")

    new_registration = New_registrations.__table__.insert().values(
        date_now=naive_current_time,
        username=username,
        fullname=fullname,
        phone=phone,
        city=city,
        activity_type=activity_type,
        contacts_link=contacts_link
    )
    await db.execute(new_registration)
    await db.commit()

    return {"message": "Форма успешно отправлена"}


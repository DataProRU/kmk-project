from fastapi import APIRouter, Form, Request, File, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from database import get_db, Activity_types, New_registrations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import gspread
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import tempfile
import pytz

router = APIRouter()
templates = Jinja2Templates(directory="templates/register_bot")

gc = gspread.service_account(filename="midyear-cursor-379909-cc15f63beea0.json")
sht2 = gc.open_by_url(
    'https://docs.google.com/spreadsheets/d/1NyHxdHhSfKZzwBghyQY6U8zl0xIWUJSn6IPEW8oTYSE/edit?usp=sharing')
worksheet_registration = sht2.get_worksheet(0)

moscow_tz = pytz.timezone('Europe/Moscow')

@router.get("/register_bot_add", response_class=HTMLResponse)
async def read_register_form(request: Request, username: str,  db: AsyncSession = Depends(get_db), ):
    stmt = select(Activity_types)
    result = await db.execute(stmt)
    activity_types = result.scalars().all()
    return templates.TemplateResponse("form.html", {"request": request,
                                                       "username": username,
                                                       "activity_types": activity_types})


@router.post("/send_registration")
async def submit(
    username: str = Form(),
    fullname: str = Form(),
    phone: str = Form(),
    city: str = Form(),
    activity_type: str = Form(),
    contacts_link: str = Form(),
    db: AsyncSession = Depends(get_db),
):

    username = username.replace("%20", " ")

    # Добавление записи в Google Таблицу
    worksheet_registration.format('A:A', {  # Форматирование столбца с датами
        "numberFormat": {
            "type": "DATE",
            "pattern": "dd/mm/yyyy"
        }
    })

    current_time = datetime.now(moscow_tz)
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M")
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


from fastapi import APIRouter, Form, Request, File, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from database import Payments, New_Reports, get_db, Metrics, Payment_types, Accounting_types
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
templates = Jinja2Templates(directory="templates")

gc = gspread.service_account(filename="midyear-cursor-379909-cc15f63beea0.json")
sht2 = gc.open_by_url(
    'https://docs.google.com/spreadsheets/d/1SnHvZLbZuZx9nTFYpAjC765K2EuCFoSnt-iYMDMZ3HU/edit?gid=0#gid=0')
worksheet_report = sht2.get_worksheet(0)
worksheet_payment = sht2.get_worksheet(1)

moscow_tz = pytz.timezone('Europe/Moscow')

@router.get("/payment", response_class=HTMLResponse)
async def read_payment_form(request: Request, username: str,  db: AsyncSession = Depends(get_db), ):
    stmt = select(Payment_types)
    result = await db.execute(stmt)
    payment_types = result.scalars().all()
    stmt = select(Accounting_types)
    result = await db.execute(stmt)
    accounting_types = result.scalars().all()
    return templates.TemplateResponse("payment.html", {"request": request,
                                                       "username": username,
                                                       "payment_types":payment_types,
                                                       "accounting_types":accounting_types})
@router.post("/send_payment")
async def submit_payment(
    username: str = Form(),
    date: str = Form(...),
    contract_number: str = Form(...),
    accounting_type: str = Form(...),
    amount: int = Form(...),
    payment_type: str = Form(...),
    comment: Optional[str] = Form(None),
    check_photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Convert date string to Date object
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    username = username.replace("%20", " ")

    # Сохранение фото на Google Диск
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'midyear-cursor-379909-cc15f63beea0.json'

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)

    # Сохранение файла во временную директорию
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await check_photo.read())
        temp_file_path = temp_file.name

    file_metadata = {'name': check_photo.filename}
    media = MediaFileUpload(temp_file_path, mimetype=check_photo.content_type, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

    file_id = file.get('id')
    photo_url = file.get('webViewLink')

    # Удаление временного файла
    os.remove(temp_file_path)

    permission = {
        'type': 'user',
        'role': 'writer',  # 'writer' для прав редактирования, 'reader' для только чтения
        'emailAddress': 'gma89618507928@gmail.com'
    }
    drive_service.permissions().create(fileId=file_id, body=permission, fields='id').execute()

    # Добавление записи в Google Таблицу
    worksheet_report.format('C:C', {  # Форматирование столбца с датами
        "numberFormat": {
            "type": "DATE",
            "pattern": "dd/mm/yyyy"
        }
    })

    current_time = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M")
    formatted_date = date_obj.strftime("%d/%m/%Y")

    new_row = [
        current_time,
        username,
        formatted_date,
        contract_number,
        accounting_type,
        amount,
        payment_type,
        photo_url,
        comment
    ]
    worksheet_report.append_row(new_row, value_input_option="USER_ENTERED")

    # Ensure date_now is a datetime object
    date_now = datetime.now(moscow_tz).astimezone(pytz.utc).replace(tzinfo=None)
    date_now_plus_3_hours = date_now + timedelta(hours=3)

    new_payment = Payments.__table__.insert().values(
        date_now=date_now_plus_3_hours,
        username=username,
        date=date_obj,
        contact_number=contract_number,
        accounting_type=accounting_type,
        payment_type=payment_type,
        check_photo=photo_url,
        comment=comment
    )
    await db.execute(new_payment)

    return {"message": "Чек успешно отправлен", "photo_url": photo_url}


@router.get("/report/{tg_username}", response_class=HTMLResponse)
async def read_root(request: Request, username: str, tg_username: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Metrics)
    result = await db.execute(stmt)
    all_metrics = result.scalars().all()
    return templates.TemplateResponse("report.html", {"request": request, "username": username,
                                                      "tg_username": tg_username,
                                                      "all_metrics":all_metrics})

@router.post("/send_report")
async def submit_report(
        date: str = Form(...),
        username: str = Form(...),
        tg_username: str = Form(...),
        accounting_type: str = Form(...),
        check_photo: UploadFile = File(...),
        comment: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
):
    # Сохранение фото на Google Диск
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'midyear-cursor-379909-cc15f63beea0.json'
    username = username.replace("%20", " ")

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)

    # Сохранение файла во временную директорию
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await check_photo.read())
        temp_file_path = temp_file.name

    file_metadata = {'name': check_photo.filename}
    media = MediaFileUpload(temp_file_path, mimetype=check_photo.content_type, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

    photo_url = file.get('webViewLink')
    file_id = file.get('id')

    # Удаление временного файла
    os.remove(temp_file_path)

    permission = {
        'type': 'user',
        'role': 'writer',  # 'writer' для прав редактирования, 'reader' для только чтения
        'emailAddress': 'gma89618507928@gmail.com'
    }
    drive_service.permissions().create(fileId=file_id, body=permission, fields='id').execute()

    # Установите формат даты для всего столбца D
    worksheet_payment.format('D:D', {
        "numberFormat": {
            "type": "DATE",
            "pattern": "dd/mm/yyyy"
        }
    })

    current_time = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M")
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    formatted_date = date_obj.strftime("%d/%m/%Y")  # Если нужно отобразить как dd.mm.yyyy

    new_row = [
        str(current_time),
        str(tg_username),
        str(username),
        formatted_date,
        str(accounting_type),
        str(photo_url),
        str(comment)
    ]
    worksheet_payment.append_row(new_row, value_input_option="USER_ENTERED")

    new_payment = New_Reports.__table__.insert().values(
        date=date_obj,
        username=username,
        tg_username=tg_username,
        accounting_type=accounting_type,
        check_photo=photo_url,
        comment=comment
    )
    await db.execute(new_payment)

    return {"message": "Отчет успешно отправлен"}

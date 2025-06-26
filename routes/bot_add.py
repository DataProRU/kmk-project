from fastapi import APIRouter, Form, Request, File, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from database import Payments, get_db, Metrics, Payment_types, Accounting_types
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
import textwrap
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="templates")

gc = gspread.service_account(filename=os.getenv("GOOGLE_TABLES_CREDENTIALS_FILE"))
sht2 = gc.open_by_url(os.getenv("GOOGLE_TABLES_BOT_ADD_URL"))
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
import requests

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("BOT_CHAT_ID")

# Ваши настройки для Google Drive и Google Sheets
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_TABLES_CREDENTIALS_FILE")

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
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_TABLES_CREDENTIALS_FILE")

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
        'emailAddress': os.getenv("EMAIL")
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
    date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
    print(username)

    '''stmt = select(Users).where(Users.tg_username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Если пользователь не найден, можно вернуть ошибку или выполнить другие действия
        return "not"

    # Получаем username из найденного пользователя
    full_username = user.username'''

    # Форматируем дату с использованием точек
    formatted_date_with_dots = date_obj.strftime("%d.%m.%Y")

    telegram_message = textwrap.dedent(f"""
           💵 Новое поступление
           #{accounting_type} {amount} руб.
           Тип оплаты: {payment_type}
           от {formatted_date_with_dots}

           Внес: #{username}
           № договора: {contract_number}
           Примечание: {comment if comment else "Нет примечания"}

           <a href="{photo_url}">Ссылка на чек</a>
       """).strip()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    print(response.text)

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
        contract_number: str = Form(...),
        username: str = Form(...),
        tg_username: str = Form(...),
        accounting_type: str = Form(...),
        check_photo: UploadFile = File(...),
        comment: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
):
    # Сохранение фото на Google Диск
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_TABLES_CREDENTIALS_FILE")
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
        'role': 'writer',
        'emailAddress': os.getenv("EMAIL")
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

    new_row = [
        str(current_time),
        str(tg_username),
        str(username),
        str(contract_number),
        str(accounting_type),
        str(photo_url),
        str(comment)
    ]
    worksheet_payment.append_row(new_row, value_input_option="USER_ENTERED")

    '''new_payment = New_Reports.__table__.insert().values(
        contract_number=contract_number,
        username=username,
        tg_username=tg_username,
        accounting_type=accounting_type,
        check_photo=photo_url,
        comment=comment,
        date=datetime.now(moscow_tz).date()  # Добавляем текущую дату
    )
    await db.execute(new_payment)'''

    date = datetime.now(moscow_tz)

    formatted_date_with_dots = date.strftime("%d.%m.%Y")

    telegram_message = textwrap.dedent(f"""
           💵 Новый этап договора
           от {formatted_date_with_dots}
           
           Внес: #{username}
           № договора: {contract_number}
           Этап работ: {accounting_type} 
           Примечание: {comment if comment else "Нет примечания"}

           <a href="{photo_url}">Ссылка на чек</a>
       """).strip()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

    return {"message": "Отчет успешно отправлен"}
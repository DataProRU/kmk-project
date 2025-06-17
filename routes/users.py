from fastapi import APIRouter, Request, Form, Depends
from database import WebUser, get_db
from models import UpdateUserRole, User
from fastapi.templating import Jinja2Templates
from dependencies import get_token_from_cookie, get_current_user
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import update
from passlib.context import CryptContext

router = APIRouter()
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/users/")
async def get_users(request: Request, db: AsyncSession = Depends(get_db)):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    role = payload.get("role")
    if role != "admin":
        return templates.TemplateResponse("not_access.html", {"request": request})

    stmt = select(WebUser)
    result = await db.execute(stmt)
    users_data = result.scalars().all()
    return templates.TemplateResponse("access.html", {"request": request, "users": users_data})

@router.delete("/users/{user_id}/")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    role = payload.get("role")
    if role != "admin":
        return JSONResponse({"detail": "Access denied"}, status_code=403)

    # Удаляем пользователя
    stmt = select(WebUser).where(WebUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        await db.delete(user)
        await db.commit()
        return JSONResponse({"detail": "User deleted successfully"})
    return JSONResponse({"detail": "User not found"}, status_code=404)

@router.get("/users/{user_id}/edit/")
async def edit_user_form(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    role = payload.get("role")
    if role != "admin":
        return templates.TemplateResponse("not_access.html", {"request": request})

    # Получаем данные пользователя
    stmt = select(WebUser).where(WebUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse("not_found.html", {"request": request})

    return templates.TemplateResponse("edit_user.html", {"request": request, "user": user})

@router.post("/users/{user_id}/edit/")
async def update_user(
    request: Request,
    user_id: int,
    username: str = Form(...),
    role: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    user_role = payload.get("role")
    if user_role != "admin":
        return templates.TemplateResponse("not_access.html", {"request": request})

    # Проверяем, существует ли пользователь
    stmt = select(WebUser).where(WebUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse("not_found.html", {"request": request})

    # Обновляем данные пользователя
    user.username = username
    user.role = role
    await db.commit()

    return RedirectResponse(url="/users/", status_code=303)

@router.post("/users/add/")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    if payload.get("role") != "admin":
        return templates.TemplateResponse("not_access.html", {"request": request})

    # Хешируем пароль перед сохранением
    hashed_password = pwd_context.hash(password)

    # Добавляем нового пользователя
    new_user = WebUser(username=username, password=hashed_password, role=role)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RedirectResponse(url="/users/", status_code=303)

@router.post("/users/{user_id}/delete/")
async def delete_user_post(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = get_token_from_cookie(request)
    if isinstance(token, RedirectResponse):
        return token

    payload = get_current_user(token)
    if isinstance(payload, RedirectResponse):
        return payload

    if payload.get("role") != "admin":
        return templates.TemplateResponse("not_access.html", {"request": request})

    # Удаляем пользователя
    stmt = select(WebUser).where(WebUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        await db.delete(user)
        await db.commit()

    return RedirectResponse(url="/users/", status_code=303)

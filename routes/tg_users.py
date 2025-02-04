from fastapi import APIRouter, Request, Form, Depends
from database import Users, get_db
from fastapi.templating import Jinja2Templates
from dependencies import get_token_from_cookie, get_current_user
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext

router = APIRouter()
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/tg_users/")
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

    stmt = select(Users)
    result = await db.execute(stmt)
    users_data = result.scalars().all()

    return templates.TemplateResponse("tg_access.html", {"request": request, "users": users_data})

@router.delete("/tg_users/{user_id}/")
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
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        await db.delete(user)
        await db.commit()
        return JSONResponse({"detail": "User deleted successfully"})
    return JSONResponse({"detail": "User not found"}, status_code=404)

@router.get("/tg_users/{user_id}/edit/")
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
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse("not_found.html", {"request": request})

    return templates.TemplateResponse("edit_user.html", {"request": request, "user": user})

@router.post("/tg_users/{user_id}/edit/")
async def update_user(
    request: Request,
    user_id: int,
    tg_username: str = Form(...),
    username: str = Form(...),
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
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.username = username
        user.tg_username = tg_username
        await db.commit()

    return RedirectResponse(url="/tg_users/", status_code=303)

@router.post("/tg_users/add/")
async def add_user(
    request: Request,
    tg_username: str = Form(...),
    username: str = Form(...),
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

    # Добавляем нового пользователя
    new_user = Users(tg_username=tg_username, username=username)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RedirectResponse(url="/tg_users/", status_code=303)

@router.post("/tg_users/{user_id}/delete/")
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
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        await db.delete(user)
        await db.commit()

    return RedirectResponse(url="/tg_users/", status_code=303)

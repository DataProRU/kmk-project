from fastapi import APIRouter, Request, Form, Depends, HTTPException
from database import Accounting_types, get_db
from fastapi.templating import Jinja2Templates
from dependencies import get_token_from_cookie, get_current_user
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates/directory/")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/accounting_types/")
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

    try:
        stmt = select(Accounting_types)
        result = await db.execute(stmt)
        users_data = result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return templates.TemplateResponse("accounting_types.html", {"request": request, "users": users_data})

@router.delete("/accounting_types/{user_id}/")
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

    try:
        stmt = select(Accounting_types).where(Accounting_types.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            await db.delete(user)
            await db.commit()
            return JSONResponse({"detail": "User deleted successfully"})
        return JSONResponse({"detail": "User not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/accounting_types/{user_id}/edit/")
async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
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

    try:
        stmt = select(Accounting_types).where(Accounting_types.id == user_id)
        result = await db.execute(stmt)
        metrics = result.scalar_one_or_none()

        if metrics:
            metrics.name = name
            await db.commit()
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/accounting_types/", status_code=303)

@router.post("/accounting_types/add/")
async def add_user(
    request: Request,
    name: str = Form(...),
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

    try:
        metrics = Accounting_types(name=name)  # Do not set the id manually
        db.add(metrics)
        await db.commit()
        await db.refresh(metrics)
        logger.info(f"Metric added successfully: {metrics}")
    except Exception as e:
        logger.error(f"Error adding metric: {e}")
        await db.rollback()  # Rollback the transaction in case of an error
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/accounting_types/", status_code=303)

@router.post("/accounting_types/{user_id}/delete/")
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

    try:
        stmt = select(Accounting_types).where(Accounting_types.id == user_id)
        result = await db.execute(stmt)
        metrics = result.scalar_one_or_none()

        if metrics:
            await db.delete(metrics)
            await db.commit()
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/accounting_types/", status_code=303)

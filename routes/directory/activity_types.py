from fastapi import APIRouter, Request, Form, Depends, HTTPException
from database import Activity_types, get_db
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

@router.get("/activity_types/")
async def get_activity_types(request: Request, db: AsyncSession = Depends(get_db)):
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
        stmt = select(Activity_types)
        result = await db.execute(stmt)
        activity_types_data = result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching activity types: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return templates.TemplateResponse("activity_types.html", {"request": request, "activity_types": activity_types_data})

@router.delete("/activity_types/{activity_type_id}/")
async def delete_activity_type(
    activity_type_id: int,
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
        stmt = select(Activity_types).where(Activity_types.id == activity_type_id)
        result = await db.execute(stmt)
        activity_type = result.scalar_one_or_none()

        if activity_type:
            await db.delete(activity_type)
            await db.commit()
            return JSONResponse({"detail": "Activity type deleted successfully"})
        return JSONResponse({"detail": "Activity type not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error deleting activity type: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/activity_types/{activity_type_id}/edit/")
async def update_activity_type(
    request: Request,
    activity_type_id: int,
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
        stmt = select(Activity_types).where(Activity_types.id == activity_type_id)
        result = await db.execute(stmt)
        activity_type = result.scalar_one_or_none()

        if activity_type:
            activity_type.name = name
            await db.commit()
    except Exception as e:
        logger.error(f"Error updating activity type: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/activity_types/", status_code=303)

@router.post("/activity_types/add/")
async def add_activity_type(
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
        activity_type = Activity_types(name=name)  # Do not set the id manually
        db.add(activity_type)
        await db.commit()
        await db.refresh(activity_type)
        logger.info(f"Activity type added successfully: {activity_type}")
    except Exception as e:
        logger.error(f"Error adding activity type: {e}")
        await db.rollback()  # Rollback the transaction in case of an error
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/activity_types/", status_code=303)

@router.post("/activity_types/{activity_type_id}/delete/")
async def delete_activity_type_post(
    activity_type_id: int,
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
        stmt = select(Activity_types).where(Activity_types.id == activity_type_id)
        result = await db.execute(stmt)
        activity_type = result.scalar_one_or_none()

        if activity_type:
            await db.delete(activity_type)
            await db.commit()
    except Exception as e:
        logger.error(f"Error deleting activity type: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/activity_types/", status_code=303)
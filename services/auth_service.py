from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from services.auth import verify_password, get_password_hash, create_access_token
from schemas import UserCreate
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database  import WebUser # Assuming you have a User model

async def register_user(
    request: Request,
    username: str,
    password: str,
    role: str,
    db: AsyncSession,
    templates,
):
    user = UserCreate(username=username, password=password, role=role)
    try:
        new_user = WebUser(username=user.username, password=get_password_hash(user.password), role=user.role)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return RedirectResponse("/users", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": str(e)}
        )

async def login_user(request: Request, form_data, db: AsyncSession, templates):
    try:
        # Use SQLAlchemy's select statement
        stmt = select(WebUser).where(WebUser.username == form_data.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # Проверка, найден ли пользователь и совпадает ли пароль
        if user and verify_password(form_data.password, user.password):
            # Генерация токена и установка куки
            token = create_access_token(
                {"sub": form_data.username, "role": user.role}
            )
            response = RedirectResponse(
                url="/welcome", status_code=status.HTTP_303_SEE_OTHER
            )
            response.set_cookie(key="token", value=token, httponly=True)
            return response

        # Ошибка авторизации
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password"}
        )

    except Exception as e:
        # Логирование ошибки для отладки (по желанию)
        print(f"Error logging in: {e}")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "An error occurred"}
        )

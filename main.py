from fastapi import FastAPI, Request, Depends, status, HTTPException, Form, File, UploadFile
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from database import Base, engine, get_db
from typing import Optional
from datetime import datetime
import os
import uuid

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler as default_http_handler
from fastapi.responses import Response

from routers.auth import router as auth_router
from routers.customer import router as customer_router
from routers.chef import router as chef_router
from routers.voice import router as voice_router
from routers.notification import router as notification_router
from routers.dish_suggestions import router as dish_suggestions_router

from config import settings

from utils.dependencies import common_template_params, get_current_user
from utils.security import decode_access_token, get_password_hash, verify_password
from models.user import User

import models.user
import models.order

# 菜單建議API已移至專門的路由器

app = FastAPI(title="NTUB Project 114205")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=False,
    same_site="lax",
    max_age=14 * 24 * 60 * 60,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router, prefix="/auth")
app.include_router(customer_router, prefix="/customer")
app.include_router(chef_router, prefix="/chef")
app.include_router(voice_router)
app.include_router(notification_router)
app.include_router(dish_suggestions_router)

# API 路由已就緒

# @app.get("/")
# def index(request: Request, db=Depends(get_db)):
#     avatar_url = request.cookies.get("avatar_url")
#     token = request.cookies.get("access_token")
#     from utils.security import decode_access_token
#     from models.user import User
#     if not token or not (payload := decode_access_token(token)):
#         return templates.TemplateResponse("login.html", {"request": request})
#     user = db.query(User).get(payload.get("user_id"))
#     if not user:
#         return templates.TemplateResponse("login.html", {"request": request})
#     return templates.TemplateResponse("index.html", {"request": request, "user": user, "avatar_url": avatar_url})

@app.get("/", name="index")
def index(ctx: dict = Depends(common_template_params)):
    return templates.TemplateResponse("index.html", ctx)

# 菜單建議API已移至 routers/dish_suggestions.py

# 通用個人資料更新API
@app.post("/profile/update")
async def update_profile(
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        # 更新基本資料
        current_user.name = name
        if phone:
            current_user.phone = phone
        
        # 處理密碼更新
        if new_password:
            if not current_password:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "請輸入目前密碼"}
                )
            
            # 驗證目前密碼（OAuth用戶可能沒有密碼）
            if current_user.hashed_password and not verify_password(current_password, current_user.hashed_password):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "目前密碼錯誤"}
                )
            
            # 設置新密碼
            current_user.hashed_password = get_password_hash(new_password)
        
        # 處理頭像上傳
        if avatar and avatar.filename:
            # 確保uploads目錄存在
            os.makedirs("static/uploads/avatars", exist_ok=True)
            
            # 生成唯一檔名
            file_extension = avatar.filename.split('.')[-1] if '.' in avatar.filename else 'jpg'
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"static/uploads/avatars/{filename}"
            
            # 儲存檔案
            with open(file_path, "wb") as buffer:
                content = await avatar.read()
                buffer.write(content)
            
            current_user.avatar_url = f"/static/uploads/avatars/{filename}"
        
        # 更新時間戳
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content={"success": True, "message": "個人資料更新成功！"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"更新失敗：{str(e)}"}
        )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=status.HTTP_404_NOT_FOUND
        )
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return templates.TemplateResponse(
            "401.html",
            {"request": request},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return await default_http_handler(request, exc)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return templates.TemplateResponse(
            "401.html",
            {"request": request},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return await default_http_handler(request, exc)

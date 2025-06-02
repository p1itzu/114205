from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
import secrets
import os
import shutil
from datetime import datetime, timedelta
from PIL import Image

from config import settings
from database import get_db
from models.user import User, UserRole
from models.chef import ChefProfile
from utils.security import verify_password, get_password_hash, create_access_token
from utils.mail import sendmail

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def issue_login_cookie_and_redirect(user: User):
    token = create_access_token({"user_id": user.id})
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return resp

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.hashed_password or ""):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "帳號或密碼錯誤"}
        )
    
    # 檢查信箱是否已驗證（OAuth 用戶跳過檢查）
    if not user.oauth_provider and not user.email_verified:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "請先驗證您的信箱後再登入", "show_resend": True, "email": user.email}
        )
    
    # 檢查廚師是否需要完善資料
    if user.role == UserRole.CHEF:
        chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == user.id).first()
        if not chef_profile or not chef_profile.certificate_image_url:
            request.session["chef_user_id"] = user.id
            return RedirectResponse(url="/auth/upload-certificate", status_code=status.HTTP_302_FOUND)
    
    token = create_access_token({"user_id": user.id})
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie("access_token", token, httponly=True)
    return resp

@router.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
    ):
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Email 已被註冊"}
        )

    # 驗證角色
    try:
        user_role = UserRole(role)
    except ValueError:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "無效的用戶角色"}
        )

    # 生成驗證 token
    verification_token = secrets.token_urlsafe(32)
    
    hashed = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed,
        name=name,
        role=user_role,
        email_verified=False,
        verification_token=verification_token,
        verification_sent_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 如果是廚師，創建廚師資料表
    if user_role == UserRole.CHEF:
        chef_profile = ChefProfile(user_id=user.id)
        db.add(chef_profile)
        db.commit()
    
    # 發送驗證郵件
    verification_url = f"auth/verify-email/{verification_token}"
    mail_sent = sendmail(email, verification_url)
    
    if mail_sent:
        return templates.TemplateResponse(
            "signup_success.html", 
            {"request": request, "email": email}
        )
    else:
        # 如果郵件發送失敗，刪除用戶並顯示錯誤
        db.delete(user)
        db.commit()
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "郵件發送失敗，請稍後再試"}
        )

@router.get("/verify-email/{token}")
def verify_email(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    # 查找用戶
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        return templates.TemplateResponse(
            "verification_result.html",
            {"request": request, "success": False, "message": "無效的驗證連結"}
        )
    
    # 檢查連結是否過期（24小時）
    if user.verification_sent_at and datetime.utcnow() > user.verification_sent_at + timedelta(hours=24):
        return templates.TemplateResponse(
            "verification_result.html",
            {"request": request, "success": False, "message": "驗證連結已過期，請重新註冊"}
        )
    
    # 驗證成功
    user.email_verified = True
    user.verification_token = None
    user.verification_sent_at = None
    db.commit()
    
    return templates.TemplateResponse(
        "verification_result.html",
        {"request": request, "success": True, "message": "信箱驗證成功！您現在可以登入了"}
    )

@router.post("/resend-verification")
def resend_verification(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "找不到此信箱"}
        )
    
    if user.email_verified:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "此信箱已經驗證過了"}
        )
    
    # 生成新的驗證 token
    verification_token = secrets.token_urlsafe(32)
    user.verification_token = verification_token
    user.verification_sent_at = datetime.utcnow()
    db.commit()
    
    # 發送驗證郵件
    verification_url = f"auth/verify-email/{verification_token}"
    mail_sent = sendmail(email, verification_url)
    
    if mail_sent:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "success": "驗證郵件已重新發送，請檢查您的信箱"}
        )
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "郵件發送失敗，請稍後再試"}
        )

@router.get("/upload-certificate")
def upload_certificate_page(request: Request):
    if "chef_user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("upload_certificate.html", {"request": request})

@router.post("/upload-certificate")
async def upload_certificate(
    request: Request,
    certificate_name: str = Form(...),
    certificate_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.get('chef_user_id')
    if not user_id:
        raise HTTPException(400, "無效的操作，請重新登入")
    
    user = db.query(User).get(user_id)
    if not user or user.role != UserRole.CHEF:
        raise HTTPException(404, "找不到廚師用戶")
    
    # 獲取或創建廚師資料
    chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == user.id).first()
    if not chef_profile:
        chef_profile = ChefProfile(user_id=user.id)
        db.add(chef_profile)
        db.commit()
        db.refresh(chef_profile)
    
    # 驗證檔案類型
    if not certificate_image.content_type.startswith('image/'):
        return templates.TemplateResponse(
            "upload_certificate.html",
            {"request": request, "error": "請上傳圖片檔案"}
        )
    
    # 創建上傳目錄
    upload_dir = "static/uploads/certificates"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 生成唯一檔名
    file_extension = certificate_image.filename.split('.')[-1]
    filename = f"cert_{user.id}_{secrets.token_urlsafe(8)}.{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        # 保存原始檔案
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(certificate_image.file, buffer)
        
        # 壓縮圖片（可選）
        with Image.open(file_path) as img:
            # 如果圖片太大，調整大小
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(file_path, optimize=True, quality=85)
        
        # 更新廚師資料
        chef_profile.certificate_name = certificate_name
        chef_profile.certificate_image_url = f"/static/uploads/certificates/{filename}"
        db.commit()
        
        # 清除 session 並登入
        request.session.pop('chef_user_id', None)
        
        return templates.TemplateResponse(
            "certificate_success.html",
            {"request": request, "user": user}
        )
        
    except Exception as e:
        # 如果保存失敗，刪除檔案
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return templates.TemplateResponse(
            "upload_certificate.html",
            {"request": request, "error": f"上傳失敗：{str(e)}"}
        )

@router.get("/google/login")
async def login_google(request: Request):
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth 失敗：{e.error}")

    print("token dict:", token)

    if "userinfo" in token:
        user_info = token["userinfo"]
    elif "id_token" in token:
        user_info = await oauth.google.parse_id_token(request, token)
    else:
        userinfo_url = oauth.google.server_metadata["userinfo_endpoint"]
        resp = await oauth.google.get(userinfo_url, token=token)
        user_info = resp.json()

    print("user_info:", user_info)
    email = user_info.get("email")
    oauth_id = user_info.get("sub") or user_info.get("id")
    avatar = user_info.get("picture")
    name = user_info.get("name")
    if not email or not oauth_id:
        raise HTTPException(status_code=400, detail="無法取得 Google 使用者資訊")

    # Check if user exists by OAuth ID
    user = db.query(User).filter(
        User.oauth_provider=="google", User.oauth_id==oauth_id
    ).first()
    
    if not user:
        # Check if user exists by email
        user = db.query(User).filter(User.email==email).first()
        if user:
            # Link existing user to Google OAuth
            user.oauth_provider = "google"
            user.oauth_id = oauth_id
            user.name = name
            user.avatar_url = avatar
            user.email_verified = True  # Google 用戶自動驗證
            db.commit()
            db.refresh(user)
        else:
            # New user - create without committing yet
            user = User(
                email=email,
                oauth_provider="google",
                oauth_id=oauth_id,
                name=name,
                avatar_url=avatar,
                email_verified=True,  # Google 用戶自動驗證
                role=None  # Will be set after role selection
            )
            # Don't add to session or commit yet
    
    # If user doesn't have a role, redirect to role selection
    if not user.role:
        # For new users, we need to add them to session now but not commit
        if user.id is None:  # New user not yet in database
            db.add(user)
            db.commit()
            db.refresh(user)
        
        request.session["pending_user_id"] = user.id
        return RedirectResponse(
            url="/auth/select-role",
            status_code=status.HTTP_302_FOUND
        )
    
    # 檢查廚師是否需要上傳證照
    if user.role == UserRole.CHEF:
        chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == user.id).first()
        if not chef_profile or not chef_profile.certificate_image_url:
            request.session["chef_user_id"] = user.id
            return RedirectResponse(url="/auth/upload-certificate", status_code=status.HTTP_302_FOUND)
    
    resp = issue_login_cookie_and_redirect(user)
    if avatar:
        resp.set_cookie(key="avatar_url", value=avatar, httponly=False)

    return resp

@router.get("/select-role")
def select_role_page(request: Request):
    if "pending_user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("select_role.html", {"request": request})

@router.post("/select-role", name="select_role")
def select_role(
    request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.pop('pending_user_id', None)
    if not user_id:
        raise HTTPException(400, "無效的操作，請重新登入後再試。")
    
    # 驗證角色
    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(400, "無效的用戶角色")
    
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "找不到使用者。")
    
    user.role = user_role
    db.commit()
    db.refresh(user)

    # 如果是廚師，創建廚師資料並檢查是否需要上傳證照
    if user_role == UserRole.CHEF:
        chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == user.id).first()
        if not chef_profile:
            chef_profile = ChefProfile(user_id=user.id)
            db.add(chef_profile)
            db.commit()
        
        if not chef_profile.certificate_image_url:
            request.session["chef_user_id"] = user.id
            return RedirectResponse(url="/auth/upload-certificate", status_code=status.HTTP_302_FOUND)

    return issue_login_cookie_and_redirect(user)

@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    resp.delete_cookie("avatar_url")
    return resp
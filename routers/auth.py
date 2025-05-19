from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError

from config import settings
from database import get_db
from models.user import User
from utils.security import verify_password, get_password_hash, create_access_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
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

    hashed = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed,
        name=name,
        role=role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    resp.delete_cookie("avatar_url")
    return resp

@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = f"{settings.BASE_URL}/auth/google/callback"
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

    user = db.query(User).filter(
        User.oauth_provider=="google", User.oauth_id==oauth_id
    ).first()
    if not user:
        user = db.query(User).filter(User.email==email).first()
        if user:
            user.oauth_provider = "google"
            user.oauth_id = oauth_id
            user.name = name
        else:
            user = User(
                email=email,
                oauth_provider="google",
                oauth_id=oauth_id,
                name=name
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"user_id": user.id})
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    if avatar:
        resp.set_cookie(
            key="avatar_url",
            value=avatar,
            httponly=False,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    return resp

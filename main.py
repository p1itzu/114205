from fastapi import FastAPI, Request, Depends
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine, get_db

from routers.auth import router as auth_router
from routers.customer import router as customer_router
from routers.chef import router as chef_router

from config import settings

from utils.security import decode_access_token
from models.user import User

import models.user
import models.order

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

@app.get("/")
def index(request: Request, db=Depends(get_db)):
    token = request.cookies.get("access_token")
    user = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user = db.query(User).get(payload["user_id"])

    avatar_url = request.cookies.get("avatar_url")
    return templates.TemplateResponse(
       "index.html",
       {"request": request, "user": user, "avatar_url": avatar_url}
    )
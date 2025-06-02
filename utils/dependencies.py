from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from utils.security import decode_access_token
from models.user import User, UserRole

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="請先登入")
    payload = decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的登入狀態")
    user = db.query(User).get(payload["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者不存在")
    return user

def require_customer(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=404, detail="Not Found")
    return user

def require_chef(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.CHEF:
        raise HTTPException(status_code=404, detail="Not Found")
    return user

def common_template_params(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    user = None
    avatar = None

    if token:
        payload = decode_access_token(token)
        if payload and "user_id" in payload:
            user = db.query(User).get(payload["user_id"])
    
    # 使用用戶的 avatar_url 或默認頭像
    if user and user.avatar_url:
        avatar = user.avatar_url
    else:
        avatar = request.cookies.get("avatar_url", "/static/imgs/avatar.png")

    return {
        "request": request,
        "user": user,
        "avatar_url": avatar
    }
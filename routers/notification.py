from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime

from database import get_db
from models import Notification, NotificationType, User, Order, Review
from utils.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Pydantic 模型
class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType
    title: str
    content: str
    order_id: Optional[int] = None
    review_id: Optional[int] = None

# 獲取通知列表
@router.get("")
def get_notifications(
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """獲取用戶通知列表"""
    try:
        # 建立查詢
        query = db.query(Notification).filter(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        # 計算總數和未讀數
        total_count = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).count()
        
        # 分頁查詢
        offset = (page - 1) * per_page
        notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(per_page).all()
        
        # 格式化通知數據
        notifications_data = []
        for notification in notifications:
            # 計算相對時間
            time_diff = datetime.utcnow() - notification.created_at
            if time_diff.days > 0:
                time_str = f"{time_diff.days}天前"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours}小時前"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes}分鐘前"
            else:
                time_str = "剛剛"
            
            notifications_data.append({
                "id": notification.id,
                "type": notification.type.value,
                "title": notification.title,
                "content": notification.content,
                "is_read": notification.is_read,
                "created_at": notification.created_at.strftime("%Y-%m-%d %H:%M"),
                "time_ago": time_str,
                "order_id": notification.order_id,
                "review_id": notification.review_id
            })
        
        return JSONResponse({
            "success": True,
            "data": {
                "notifications": notifications_data,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": (total_count + per_page - 1) // per_page,
                    "has_next": page * per_page < total_count,
                    "has_prev": page > 1
                },
                "unread_count": unread_count
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"獲取通知失敗：{str(e)}"}
        )

# 標記單個通知為已讀
@router.post("/{notification_id}/mark_read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """標記單個通知為已讀"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "通知不存在"}
            )
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "已標記為已讀"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"標記失敗：{str(e)}"}
        )

# 標記所有通知為已讀
@router.post("/mark_all_read")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """標記所有通知為已讀"""
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "所有通知已標記為已讀"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"標記失敗：{str(e)}"}
        )

# 清空所有通知
@router.delete("/clear")
def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空所有通知"""
    try:
        db.query(Notification).filter(Notification.user_id == current_user.id).delete()
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "所有通知已清空"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"清空失敗：{str(e)}"}
        )

# 獲取未讀通知數量
@router.get("/unread_count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """獲取未讀通知數量"""
    try:
        unread_count = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).count()
        
        return JSONResponse({
            "success": True,
            "unread_count": unread_count
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"獲取失敗：{str(e)}"}
        )

# 創建通知的工具函數（供其他模組使用）
def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    content: str,
    order_id: Optional[int] = None,
    review_id: Optional[int] = None
):
    """創建新通知"""
    try:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            order_id=order_id,
            review_id=review_id
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
        
    except Exception as e:
        db.rollback()
        print(f"創建通知失敗：{str(e)}")
        return None

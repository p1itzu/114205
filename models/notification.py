from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class NotificationType(enum.Enum):
    ORDER_ACCEPTED = "order_accepted"           # 訂單被接受
    ORDER_REJECTED = "order_rejected"           # 訂單被拒絕
    ORDER_NEGOTIATION = "order_negotiation"     # 議價通知
    ORDER_STATUS_UPDATE = "order_status_update" # 訂單狀態更新
    ORDER_READY = "order_ready"                 # 訂單製作完成
    ORDER_COMPLETED = "order_completed"         # 訂單完成
    NEW_ORDER = "new_order"                     # 新訂單（給廚師）
    NEW_REVIEW = "new_review"                   # 新評價
    REVIEW_REPLY = "review_reply"               # 評價回覆
    NEGOTIATION_RESPONSE = "negotiation_response" # 議價回應

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 接收者
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 通知內容
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    
    # 相關資源ID（可選）
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True)
    
    # 狀態
    is_read = Column(Boolean, default=False)
    
    # 時間
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # 關聯
    user = relationship("User", back_populates="notifications")
    order = relationship("Order")
    review = relationship("Review")

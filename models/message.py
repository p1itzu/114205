from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 關聯
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # 可選：關聯到特定訂單
    
    # 訊息內容
    subject = Column(String(200), nullable=True)  # 主題
    content = Column(Text, nullable=False)  # 訊息內容
    message_type = Column(String(50), default="text")  # 訊息類型：text, image, system
    
    # 狀態
    is_read = Column(Boolean, default=False)  # 是否已讀
    is_system = Column(Boolean, default=False)  # 是否為系統訊息
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)  # 已讀時間
    
    # 關聯
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="received_messages", foreign_keys=[receiver_id])
    order = relationship("Order") 
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    CHEF = "chef"

class User(Base):
    __tablename__ = "users"
    
    # 基本資料
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # OAuth用戶可能沒有密碼
    
    # OAuth相關
    oauth_provider = Column(String(50), nullable=True)  # 'google' 或 null
    oauth_id = Column(String(255), nullable=True)
    
    # 個人資訊
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)  # 頭像URL
    
    # 帳戶設定
    role = Column(Enum(UserRole), nullable=True)  # Allow null for OAuth users who haven't selected role yet
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    
    # 身心障礙者/高齡者驗證
    special_needs_type = Column(String(50), nullable=True)  # 'disability' 或 'elderly'
    special_needs_document_url = Column(String(500), nullable=True)  # 證明文件URL
    special_needs_verified = Column(Boolean, default=False)  # 是否已驗證
    special_needs_applied_at = Column(DateTime, nullable=True)  # 申請時間
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    chef_profile = relationship("ChefProfile", back_populates="user", uselist=False)
    orders_as_customer = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")
    orders_as_chef = relationship("Order", back_populates="chef", foreign_keys="Order.chef_id")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="receiver", foreign_keys="Message.receiver_id")
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 關聯
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 評價者（顧客）
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 被評價者（廚師）
    
    # 評價內容
    rating = Column(Integer, nullable=False)  # 1-5星
    title = Column(String(100), nullable=True)  # 評價標題
    content = Column(Text, nullable=True)  # 評價內容
    
    # 細項評分
    taste_rating = Column(Integer, nullable=True)      # 口味評分
    service_rating = Column(Integer, nullable=True)    # 服務評分
    hygiene_rating = Column(Integer, nullable=True)    # 衛生評分
    delivery_rating = Column(Integer, nullable=True)   # 配送評分
    
    # 狀態
    is_public = Column(Boolean, default=True)  # 是否公開顯示
    is_verified = Column(Boolean, default=False)  # 是否已驗證
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    order = relationship("Order", back_populates="review")
    reviewer = relationship("User", back_populates="reviews_given", foreign_keys=[reviewer_id])
    reviewee = relationship("User", back_populates="reviews_received", foreign_keys=[reviewee_id]) 
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class ChefProfile(Base):
    __tablename__ = "chef_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # 廚房資訊
    kitchen_address = Column(Text, nullable=True)  # 廚房地址
    service_area = Column(String(500), nullable=True)  # 服務範圍
    
    # 證照資訊
    certificate_name = Column(String(255), nullable=True)
    certificate_image_url = Column(String(500), nullable=True)
    certificate_verified = Column(Boolean, default=False)
    
    # 專業資訊
    experience_years = Column(Integer, nullable=True)  # 經驗年數
    description = Column(Text, nullable=True)  # 自我介紹
    
    # 評價統計
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_orders = Column(Integer, default=0)
    
    # 狀態
    is_available = Column(Boolean, default=True)  # 是否接單
    is_verified = Column(Boolean, default=False)  # 是否已認證
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    user = relationship("User", back_populates="chef_profile")
    specialties = relationship("ChefSpecialty", back_populates="chef")
    signature_dishes = relationship("ChefSignatureDish", back_populates="chef")

class ChefSpecialty(Base):
    __tablename__ = "chef_specialties"
    
    id = Column(Integer, primary_key=True, index=True)
    chef_id = Column(Integer, ForeignKey("chef_profiles.id"), nullable=False)
    specialty = Column(String(100), nullable=False)  # 例如：川菜、粵菜、義式料理
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    chef = relationship("ChefProfile", back_populates="specialties")

class ChefSignatureDish(Base):
    __tablename__ = "chef_signature_dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    chef_id = Column(Integer, ForeignKey("chef_profiles.id"), nullable=False)
    
    dish_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    price = Column(Float, nullable=True)  # 建議價格
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    chef = relationship("ChefProfile", back_populates="signature_dishes") 
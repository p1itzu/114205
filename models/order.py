from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class OrderStatus(enum.Enum):
    PENDING = "pending"              # 等待回應
    NEGOTIATING = "negotiating"      # 議價中
    ACCEPTED = "accepted"            # 已接單（議價完成）
    PREPARING = "preparing"          # 製作中
    READY = "ready"                 # 製作完成
    COMPLETED = "completed"          # 交付完成
    CANCELLED = "cancelled"          # 已取消

class DeliveryMethod(enum.Enum):
    PICKUP = "pickup"           # 自取
    DELIVERY = "delivery"       # 外送

class SpiceLevel(enum.Enum):
    NONE = "none"              # 不辣
    MILD = "mild"              # 微辣
    MEDIUM = "medium"          # 中辣
    SPICY = "spicy"            # 辣
    VERY_SPICY = "very_spicy"  # 超辣

class SaltLevel(enum.Enum):
    LIGHT = "light"            # 清淡
    NORMAL = "normal"          # 正常
    HEAVY = "heavy"            # 重鹹

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 關聯用戶
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chef_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 接單後才有值
    
    # 訂單基本資訊
    order_number = Column(String(50), unique=True, nullable=False)  # 訂單編號
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # 取餐資訊
    delivery_method = Column(Enum(DeliveryMethod), nullable=False)
    delivery_address = Column(Text, nullable=True)  # 外送地址
    delivery_notes = Column(Text, nullable=True)    # 配送備註
    
    # 時間資訊
    preferred_time = Column(DateTime, nullable=True)  # 希望完成時間
    accepted_at = Column(DateTime, nullable=True)     # 接單時間
    ready_at = Column(DateTime, nullable=True)        # 製作完成時間
    completed_at = Column(DateTime, nullable=True)    # 完成時間
    
    # 價格資訊
    total_amount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    original_amount = Column(Float, nullable=True)    # 原始報價
    negotiated_amount = Column(Float, nullable=True)  # 議價金額
    negotiation_count = Column(Integer, default=0)    # 議價次數
    
    # 備註
    customer_notes = Column(Text, nullable=True)  # 客戶備註
    chef_notes = Column(Text, nullable=True)      # 廚師備註
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    customer = relationship("User", back_populates="orders_as_customer", foreign_keys=[customer_id])
    chef = relationship("User", back_populates="orders_as_chef", foreign_keys=[chef_id])
    dishes = relationship("OrderDish", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    negotiations = relationship("Negotiation", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False)

class OrderDish(Base):
    __tablename__ = "order_dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # 菜品基本資訊
    dish_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=True)
    
    # 口味設定
    salt_level = Column(Enum(SaltLevel), default=SaltLevel.NORMAL)
    spice_level = Column(Enum(SpiceLevel), default=SpiceLevel.NONE)
    
    # 辛香料設定 (JSON格式或布林值)
    include_onion = Column(Boolean, default=True)      # 蔥
    include_ginger = Column(Boolean, default=True)     # 薑
    include_garlic = Column(Boolean, default=True)     # 蒜
    include_cilantro = Column(Boolean, default=True)   # 香菜
    
    # 其他設定
    ingredients = Column(Text, nullable=True)          # 食材需求
    special_instructions = Column(Text, nullable=True) # 特殊作法
    custom_notes = Column(Text, nullable=True)         # 客製備註
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    order = relationship("Order", back_populates="dishes")

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    old_status = Column(Enum(OrderStatus), nullable=True)
    new_status = Column(Enum(OrderStatus), nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    order = relationship("Order", back_populates="status_history")

class Negotiation(Base):
    __tablename__ = "negotiations"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # 議價資訊
    proposed_amount = Column(Float, nullable=False)    # 提議金額
    proposed_by = Column(String(20), nullable=False)   # 提議人（chef/customer）
    message = Column(Text, nullable=True)              # 議價說明
    
    # 狀態
    is_accepted = Column(Boolean, nullable=True)       # 是否被接受（None=待回應）
    response_message = Column(Text, nullable=True)     # 回應訊息
    
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    
    # 關聯
    order = relationship("Order", back_populates="negotiations")

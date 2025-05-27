import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, Date, Time, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base

class OrderStatusEnum(str, enum.Enum):
    waiting = "等待回應"
    negotiating = "議價中"
    accepted = "已接單"
    in_production = "製作中"
    production_completed = "製作完成"
    delivered = "交付完成"

class Order(Base):
    __tablename__ = "orders"
    id            = Column(Integer, primary_key=True, index=True)
    order_date    = Column(Date,   nullable=False)
    order_time    = Column(Time,   nullable=False)
    pickup_method = Column(String(50), nullable=False)
    address       = Column(String(255), nullable=True)
    contact_phone = Column(String(20),  nullable=True)
    total_price   = Column(Integer,    nullable=True)

    customer_id    = Column(Integer, ForeignKey('users.id'), nullable=True)

    customer       = relationship('User', back_populates='orders')
    dishes = relationship(
        "Dish",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.waiting, nullable=False)

class Dish(Base):
    __tablename__ = "dishes"
    id              = Column(Integer, primary_key=True, index=True)
    order_id        = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_name       = Column(String(100), nullable=False)
    quantity        = Column(Integer, nullable=False)
    special_recipe  = Column(Text,    nullable=True)
    customer_note   = Column(Text,    nullable=True)
    saltiness       = Column(Integer, CheckConstraint("saltiness BETWEEN 0 AND 10"), nullable=False)
    spiciness       = Column(Integer, CheckConstraint("spiciness BETWEEN 0 AND 10"), nullable=False)
    oiliness        = Column(Integer, CheckConstraint("oiliness BETWEEN 0 AND 10"), nullable=False)
    aroma           = Column(Integer, CheckConstraint("aroma BETWEEN 0 AND 10"), nullable=False)
    price           = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="dishes")
    ingredients = relationship(
        "DishIngredient",
        back_populates="dish",
        cascade="all, delete-orphan"
    )

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id              = Column(Integer, primary_key=True, index=True)
    dish_id         = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_name = Column(String(100), nullable=False)

    dish = relationship("Dish", back_populates="ingredients")

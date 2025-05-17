from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(Date, nullable=False)
    order_time = Column(Time, nullable=False)
    pickup_method = Column(String(50), nullable=False)
    address = Column(String(255), nullable=True)

    # Relationship to dishes
    dishes = relationship(
        "Dish",
        back_populates="order",
        cascade="all, delete-orphan"
    )

class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    special_recipe = Column(Text, nullable=True)
    customer_note = Column(Text, nullable=True)
    saltiness = Column(Integer, CheckConstraint("saltiness BETWEEN 0 AND 10"), nullable=True)
    spiciness = Column(Integer, CheckConstraint("spiciness BETWEEN 0 AND 10"), nullable=True)
    oiliness = Column(Integer, CheckConstraint("oiliness BETWEEN 0 AND 10"), nullable=True)
    aroma = Column(Integer, CheckConstraint("aroma BETWEEN 0 AND 10"), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="dishes")
    ingredients = relationship(
        "DishIngredient",
        back_populates="dish",
        cascade="all, delete-orphan"
    )

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_name = Column(String(100), nullable=False)

    # Relationship
    dish = relationship("Dish", back_populates="ingredients")
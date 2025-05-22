from pydantic import BaseModel, Field
from datetime import date, time
from typing import List, Optional

class Step1(BaseModel):
    order_date: date
    order_time: time
    pickup_method: str
    address: Optional[str] = None

class DishIn(BaseModel):
    dish_name: str
    quantity: int
    ingredients: Optional[str]
    special_recipe: Optional[str]
    customer_note: Optional[str]
    saltiness: int
    spiciness: int
    oiliness: int
    aroma: int
    dish_price: int

class Step2(BaseModel):
    dishes: List[DishIn]

class Step4(BaseModel):
    contact_phone: str
    total_price: int

class OrderCreate(BaseModel):
    step1: Step1
    step2: Step2
    step4: Step4

class SeasoningSchema(BaseModel):
    saltiness: int = Field(..., ge=0, le=10, description="鹹度")
    spiciness: int = Field(..., ge=0, le=10, description="辣度")
    oiliness: int = Field(..., ge=0, le=10, description="油度")
    aroma: int = Field(..., ge=0, le=10, description="辛香料強度")

class DishSchema(BaseModel):
    dish_name: str = Field(..., description="菜品名稱")
    quantity: int = Field(..., gt=0, description="份數")
    special_recipe: Optional[str] = Field(None, description="特製作法")
    customer_note: Optional[str] = Field(None, description="客製備註")
    seasoning: SeasoningSchema = Field(..., description="調味資料")
    ingredients: List[str] = Field(..., description="食材列表")
    price: int = Field(..., description="單道菜價格")

class OrderSchema(BaseModel):
    order_date: date = Field(..., description="訂單日期")
    order_time: time = Field(..., description="訂單時間")
    pickup_method: str = Field(..., description="取餐方式")
    address: Optional[str] = Field(None, description="取餐地址")
    dishes: List[DishSchema] = Field(..., description="訂單中包含的菜品列表")
    contact_phone: str
    total_price: int

    class Config:
        schema_extra = {
            "example": {
                "order_date": "2025-05-15",
                "order_time": "18:30:00",
                "pickup_method": "自取",
                "address": "台北市中正區XX路XX號",
                "dishes": [
                    {
                        "dish_name": "紅燒牛肉麵",
                        "quantity": 2,
                        "special_recipe": "少油",
                        "customer_note": "不要太辣",
                        "seasoning": {"saltiness": 5, "spiciness": 3, "oiliness": 4, "aroma": 6},
                        "ingredients": ["牛肉", "麵條", "青菜"]
                    }
                ]
            }
        }

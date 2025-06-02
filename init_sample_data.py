"""
測試數據初始化腳本
用於創建示例用戶和數據
"""
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, UserRole
from models.chef import ChefProfile, ChefSpecialty, ChefSignatureDish
from models.order import Order, OrderDish, OrderStatus, DeliveryMethod, SpiceLevel, SaltLevel
from utils.security import get_password_hash
from datetime import datetime, timedelta
import uuid

def create_sample_data():
    """創建示例數據"""
    db = SessionLocal()
    
    try:
        print("🍳 開始創建示例數據...")
        
        # 創建顧客用戶
        customer = User(
            email="customer@example.com",
            hashed_password=get_password_hash("password123"),
            name="王小明",
            phone="0912345678",
            role=UserRole.CUSTOMER,
            email_verified=True
        )
        db.add(customer)
        
        # 創建廚師用戶
        chef = User(
            email="chef@example.com", 
            hashed_password=get_password_hash("password123"),
            name="陳師傅",
            phone="0987654321",
            role=UserRole.CHEF,
            email_verified=True
        )
        db.add(chef)
        db.commit()
        db.refresh(chef)
        
        # 創建廚師資料
        chef_profile = ChefProfile(
            user_id=chef.id,
            kitchen_address="台北市大安區復興南路一段390號",
            service_area="台北市大安區、信義區",
            certificate_name="中式烹調丙級技術士",
            certificate_image_url="/static/uploads/certificates/sample_cert.jpg",
            certificate_verified=True,
            experience_years=8,
            description="專精台菜與粵菜，擅長家常料理與宴客菜色，注重食材新鮮與口味調配。",
            average_rating=4.5,
            total_reviews=15,
            total_orders=50,
            is_available=True,
            is_verified=True
        )
        db.add(chef_profile)
        db.commit()
        db.refresh(chef_profile)
        
        # 創建廚師專長
        specialties = ["台菜", "粵菜", "家常料理", "宴客菜"]
        for specialty in specialties:
            chef_specialty = ChefSpecialty(
                chef_id=chef_profile.id,
                specialty=specialty
            )
            db.add(chef_specialty)
        
        # 創建招牌菜
        signature_dishes = [
            {"name": "紅燒獅子頭", "description": "傳統家常菜，肉質鮮美，湯汁濃郁", "price": 280.0},
            {"name": "宮保雞丁", "description": "經典川菜，辣香適中，下飯首選", "price": 220.0},
            {"name": "糖醋排骨", "description": "酸甜開胃，老少皆宜的經典料理", "price": 320.0}
        ]
        
        for dish_data in signature_dishes:
            signature_dish = ChefSignatureDish(
                chef_id=chef_profile.id,
                dish_name=dish_data["name"],
                description=dish_data["description"],
                price=dish_data["price"]
            )
            db.add(signature_dish)
        
        db.commit()
        
        # 創建示例訂單
        order = Order(
            customer_id=customer.id,
            chef_id=chef.id,
            order_number=f"ORD{uuid.uuid4().hex[:8].upper()}",
            status=OrderStatus.COMPLETED,
            delivery_method=DeliveryMethod.DELIVERY,
            delivery_address="台北市信義區信義路五段7號",
            delivery_notes="大樓門口有管理員，請按101號電鈴",
            preferred_time=datetime.now() + timedelta(hours=2),
            accepted_at=datetime.now() - timedelta(hours=1),
            completed_at=datetime.now(),
            total_amount=650.0,
            delivery_fee=50.0,
            customer_notes="不要太鹹，微辣即可"
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # 創建訂單菜品
        dishes = [
            {
                "name": "宮保雞丁",
                "quantity": 1,
                "price": 220.0,
                "salt_level": SaltLevel.LIGHT,
                "spice_level": SpiceLevel.MILD,
                "custom_notes": "不要花生"
            },
            {
                "name": "糖醋排骨", 
                "quantity": 1,
                "price": 320.0,
                "salt_level": SaltLevel.NORMAL,
                "spice_level": SpiceLevel.NONE,
                "custom_notes": "排骨切小塊一點"
            },
            {
                "name": "白飯",
                "quantity": 2,
                "price": 30.0,
                "salt_level": SaltLevel.NORMAL,
                "spice_level": SpiceLevel.NONE
            }
        ]
        
        for dish_data in dishes:
            order_dish = OrderDish(
                order_id=order.id,
                dish_name=dish_data["name"],
                quantity=dish_data["quantity"],
                unit_price=dish_data["price"],
                salt_level=dish_data["salt_level"],
                spice_level=dish_data["spice_level"],
                custom_notes=dish_data.get("custom_notes")
            )
            db.add(order_dish)
        
        db.commit()
        
        print("✅ 示例數據創建完成！")
        print("\n👤 創建的用戶：")
        print(f"  顧客: {customer.email} / password123")
        print(f"  廚師: {chef.email} / password123")
        print(f"\n📦 創建的訂單: {order.order_number}")
        print(f"👨‍🍳 廚師資料已完整設定")
        
    except Exception as e:
        print(f"❌ 創建示例數據時發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 味你而煮 - 示例數據初始化工具")
    print("=" * 50)
    
    create_sample_data()
    print("\n🎉 示例數據初始化完成！")
    print("現在可以使用以下帳號登入測試：")
    print("  顧客: customer@example.com")
    print("  廚師: chef@example.com")
    print("  密碼: password123") 
"""
設置議價功能測試環境
"""
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models.user import User, UserRole
from models.chef import ChefProfile
from models.order import Order, OrderDish, OrderStatus, DeliveryMethod, SpiceLevel, SaltLevel, Negotiation
from utils.security import get_password_hash
from datetime import datetime, timedelta
import uuid

def setup_negotiation_test():
    """設置議價測試環境"""
    
    # 首先創建表結構
    print("🗄️ 創建數據庫表結構...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        print("🍳 創建議價測試數據...")
        
        # 檢查是否已有用戶
        existing_customer = db.query(User).filter(User.email == "customer@test.com").first()
        existing_chef = db.query(User).filter(User.email == "chef@test.com").first()
        
        if not existing_customer:
            # 創建顧客用戶
            customer = User(
                email="customer@test.com",
                hashed_password=get_password_hash("test123"),
                name="測試顧客",
                phone="0912345678",
                role=UserRole.CUSTOMER,
                email_verified=True
            )
            db.add(customer)
            print("✅ 創建測試顧客")
        else:
            customer = existing_customer
            print("✅ 使用現有測試顧客")
        
        if not existing_chef:
            # 創建廚師用戶
            chef = User(
                email="chef@test.com", 
                hashed_password=get_password_hash("test123"),
                name="測試廚師",
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
                kitchen_address="台北市大安區測試地址",
                service_area="台北市",
                certificate_verified=True,
                experience_years=5,
                description="測試廚師",
                is_available=True,
                is_verified=True
            )
            db.add(chef_profile)
            print("✅ 創建測試廚師和資料")
        else:
            chef = existing_chef
            print("✅ 使用現有測試廚師")
        
        db.commit()
        db.refresh(customer)
        db.refresh(chef)
        
        # 創建議價中的訂單
        negotiating_order = Order(
            customer_id=customer.id,
            chef_id=chef.id,
            order_number=f"NEGO{uuid.uuid4().hex[:6].upper()}",
            status=OrderStatus.NEGOTIATING,
            delivery_method=DeliveryMethod.DELIVERY,
            delivery_address="台北市信義區測試地址123號",
            preferred_time=datetime.now() + timedelta(hours=2),
            accepted_at=datetime.now() - timedelta(minutes=30),
            total_amount=500.0,
            customer_notes="測試議價訂單"
        )
        db.add(negotiating_order)
        db.commit()
        db.refresh(negotiating_order)
        print(f"✅ 創建議價測試訂單: {negotiating_order.order_number}")
        
        # 創建訂單菜品
        test_dishes = [
            {
                "name": "番茄炒蛋",
                "quantity": 2,
                "price": 150.0,
                "salt_level": SaltLevel.LIGHT,
                "spice_level": SpiceLevel.NONE
            },
            {
                "name": "宮保雞丁", 
                "quantity": 1,
                "price": 250.0,
                "salt_level": SaltLevel.NORMAL,
                "spice_level": SpiceLevel.MILD
            },
            {
                "name": "白飯",
                "quantity": 3,
                "price": 100.0,
                "salt_level": SaltLevel.NORMAL,
                "spice_level": SpiceLevel.NONE
            }
        ]
        
        for dish_data in test_dishes:
            order_dish = OrderDish(
                order_id=negotiating_order.id,
                dish_name=dish_data["name"],
                quantity=dish_data["quantity"],
                unit_price=dish_data["price"],
                salt_level=dish_data["salt_level"],
                spice_level=dish_data["spice_level"]
            )
            db.add(order_dish)
        
        # 創建廚師的初始議價
        chef_negotiation = Negotiation(
            order_id=negotiating_order.id,
            proposed_amount=500.0,
            proposed_by="chef",
            message="廚師初始估價",
            created_at=datetime.now() - timedelta(minutes=20)
        )
        db.add(chef_negotiation)
        
        # 創建顧客的再議價（這是我們要測試的關鍵）
        customer_negotiation = Negotiation(
            order_id=negotiating_order.id,
            proposed_amount=400.0,
            proposed_by="customer",
            message="我覺得價格有點高，能否降到400元？",
            is_accepted=None,  # 待回應
            created_at=datetime.now() - timedelta(minutes=10)
        )
        db.add(customer_negotiation)
        
        db.commit()
        
        print("✅ 議價測試環境設置完成！")
        print("\n📋 測試帳號：")
        print(f"  廚師: chef@test.com / test123")
        print(f"  顧客: customer@test.com / test123")
        print(f"\n📦 議價測試訂單: {negotiating_order.order_number}")
        print(f"💰 廚師估價: NT$500")
        print(f"💬 顧客議價: NT$400 (待廚師回應)")
        print("\n🎯 測試步驟：")
        print("1. 登入廚師帳號")
        print("2. 進入「議價中訂單」頁面")
        print("3. 點擊「查看訂單詳情」")
        print("4. 應該會自動跳轉到最終定價頁面")
        
    except Exception as e:
        print(f"❌ 設置議價測試環境時發生錯誤: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 味你而煮 - 議價功能測試環境設置")
    print("=" * 50)
    
    setup_negotiation_test()
    print("\n🎉 議價測試環境設置完成！") 
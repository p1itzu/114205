from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, UserRole
from models.order import Order

def fix_chef_assignment():
    db = SessionLocal()
    
    try:
        print("=== 修正廚師訂單分配 ===")
        
        # 找到第一個廚師
        first_chef = db.query(User).filter(User.role == UserRole.CHEF).first()
        
        if not first_chef:
            print("沒有找到廚師用戶")
            return
        
        print(f"將所有訂單分配給廚師: {first_chef.email} (ID: {first_chef.id})")
        
        # 將所有議價中的訂單分配給第一個廚師
        negotiating_orders = db.query(Order).filter(Order.status == 'negotiating').all()
        
        for order in negotiating_orders:
            old_chef_id = order.chef_id
            order.chef_id = first_chef.id
            print(f"訂單 {order.order_number}: 廚師ID {old_chef_id} -> {first_chef.id}")
        
        db.commit()
        
        print("\n✅ 訂單分配修正完成！")
        print(f"\n🎯 現在請使用以下帳號登入測試：")
        print(f"廚師帳號: {first_chef.email}")
        print(f"密碼: 請嘗試 'test123' 或其他您知道的密碼")
        
    except Exception as e:
        print(f"修正時發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_chef_assignment() 
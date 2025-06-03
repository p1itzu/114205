from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, UserRole
from models.order import Order, Negotiation

def check_chef_data():
    db = SessionLocal()
    
    try:
        print("=== 檢查所有廚師用戶 ===")
        chefs = db.query(User).filter(User.role == UserRole.CHEF).all()
        
        for chef in chefs:
            print(f"廚師ID: {chef.id}, 郵箱: {chef.email}, 姓名: {chef.name}")
        
        print("\n=== 檢查議價中訂單的廚師分配 ===")
        orders = db.query(Order).filter(Order.status == 'negotiating').all()
        
        for order in orders:
            print(f"訂單ID: {order.id}, 編號: {order.order_number}, 分配廚師ID: {order.chef_id}")
            
            # 查找對應的廚師
            if order.chef_id:
                chef = db.query(User).filter(User.id == order.chef_id).first()
                if chef:
                    print(f"  -> 廚師: {chef.email} ({chef.name})")
                else:
                    print(f"  -> 廚師ID {order.chef_id} 不存在!")
        
        print("\n=== 建議的測試步驟 ===")
        if chefs:
            print(f"請使用廚師帳號 {chefs[0].email} / test123 登入測試")
        
    except Exception as e:
        print(f"查詢時發生錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_chef_data() 
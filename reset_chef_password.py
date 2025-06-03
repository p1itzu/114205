from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, UserRole
from utils.security import get_password_hash

def reset_chef_password():
    db = SessionLocal()
    
    try:
        print("=== 重置廚師密碼 ===")
        
        # 找到第一個廚師
        chef = db.query(User).filter(User.email == "11336017@ntub.edu.tw").first()
        
        if not chef:
            print("沒有找到廚師帳號")
            return
        
        # 重置密碼為 test123
        chef.hashed_password = get_password_hash("test123")
        db.commit()
        
        print(f"✅ 廚師 {chef.email} 的密碼已重置為 'test123'")
        print("\n🎯 現在可以使用以下帳號登入測試：")
        print(f"廚師帳號: {chef.email}")
        print(f"密碼: test123")
        
        print("\n📋 測試步驟：")
        print("1. 登入廚師帳號")
        print("2. 進入「議價中訂單」頁面")
        print("3. 應該會看到兩個訂單，都顯示「顧客已議價」")
        print("4. 點擊「查看訂單詳情」")
        print("5. 應該會自動跳轉到最終定價頁面")
        
    except Exception as e:
        print(f"重置密碼時發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_chef_password() 
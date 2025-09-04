#!/usr/bin/env python3
"""
身心障礙者/高齡者驗證申請審核腳本
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import User
from database import get_db_engine

def approve_special_needs_by_id(user_id):
    """通過用戶ID審核申請"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ 找不到 ID 為 {user_id} 的用戶")
            return False
            
        if not user.special_needs_applied_at:
            print(f"❌ 用戶 {user.name} ({user.email}) 尚未申請身心障礙者/高齡者驗證")
            return False
            
        if user.special_needs_verified:
            print(f"ℹ️  用戶 {user.name} ({user.email}) 已經通過驗證")
            return True
            
        # 審核通過
        user.special_needs_verified = True
        session.commit()
        
        print(f"✅ 用戶 {user.name} ({user.email}) 的{user.special_needs_type}驗證已通過")
        print(f"   申請時間: {user.special_needs_applied_at}")
        print(f"   證明文件: {user.special_needs_document_url}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ 審核失敗: {e}")
        return False
    finally:
        session.close()

def approve_special_needs_by_email(email):
    """通過信箱審核申請"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ 找不到信箱為 {email} 的用戶")
            return False
            
        return approve_special_needs_by_id(user.id)
        
    except Exception as e:
        print(f"❌ 審核失敗: {e}")
        return False
    finally:
        session.close()

def list_pending_applications():
    """列出所有待審核的申請"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        pending_users = session.query(User).filter(
            User.special_needs_applied_at.isnot(None),
            User.special_needs_verified == False
        ).all()
        
        if not pending_users:
            print("📝 目前沒有待審核的申請")
            return
            
        print("📋 待審核的身心障礙者/高齡者驗證申請:")
        print("-" * 80)
        for user in pending_users:
            print(f"ID: {user.id}")
            print(f"姓名: {user.name}")
            print(f"信箱: {user.email}")
            print(f"類型: {user.special_needs_type}")
            print(f"申請時間: {user.special_needs_applied_at}")
            print(f"證明文件: {user.special_needs_document_url}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python approve_special_needs.py list                    # 列出待審核申請")
        print("  python approve_special_needs.py approve_id <user_id>    # 通過用戶ID審核")
        print("  python approve_special_needs.py approve_email <email>   # 通過信箱審核")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_pending_applications()
    elif command == "approve_id" and len(sys.argv) == 3:
        user_id = int(sys.argv[2])
        approve_special_needs_by_id(user_id)
    elif command == "approve_email" and len(sys.argv) == 3:
        email = sys.argv[2]
        approve_special_needs_by_email(email)
    else:
        print("❌ 無效的命令")
        sys.exit(1)
"""
數據庫重建腳本
警告：此腳本會刪除所有現有數據！
"""
from sqlalchemy import create_engine
from database import Base
from config import settings
from models import *  # 導入所有模型

def create_all_tables():
    """創建所有資料表"""
    print("🗄️ 開始創建資料庫表格...")
    
    # 創建數據庫引擎
    engine = create_engine(settings.DATABASE_URL)
    
    # 刪除所有現有表格
    print("⚠️ 刪除現有表格...")
    Base.metadata.drop_all(bind=engine)
    
    # 創建所有表格
    print("📝 創建新表格...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ 數據庫表格創建完成！")
    
    # 顯示創建的表格
    print("\n📋 已創建的表格：")
    tables = [
        "users - 用戶基本資料",
        "chef_profiles - 廚師詳細資料", 
        "chef_specialties - 廚師專長",
        "chef_signature_dishes - 廚師招牌菜",
        "orders - 訂單主表",
        "order_dishes - 訂單菜品明細",
        "order_status_history - 訂單狀態歷史",
        "reviews - 評價",
        "messages - 訊息溝通"
    ]
    
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")

if __name__ == "__main__":
    print("🚀 味你而煮 - 資料庫重建工具")
    print("=" * 50)
    
    confirm = input("⚠️ 此操作將刪除所有現有數據，是否繼續？(yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        create_all_tables()
        print("\n🎉 資料庫重建完成！")
    else:
        print("❌ 操作已取消") 
#!/usr/bin/env python3
"""
資料庫遷移腳本：為User模型添加身心障礙者/高齡者驗證相關欄位

新增欄位：
- special_needs_type: 驗證類型 ('disability' 或 'elderly')
- special_needs_document_url: 證明文件URL
- special_needs_verified: 是否已驗證
- special_needs_applied_at: 申請時間

使用方法：
python migrate_special_needs.py
"""

import sys
from sqlalchemy import create_engine, text
from config import settings
from datetime import datetime

def run_migration():
    """執行資料庫遷移"""
    print("🚀 開始資料庫遷移：添加身心障礙者/高齡者驗證欄位...")
    
    try:
        # 建立資料庫連接
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # 開始事務
            trans = conn.begin()
            
            try:
                print("📋 檢查現有欄位...")
                
                # 檢查欄位是否已存在（避免重複遷移）
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name IN ('special_needs_type', 'special_needs_document_url', 'special_needs_verified', 'special_needs_applied_at')
                """))
                
                existing_columns = [row[0] for row in result.fetchall()]
                
                if existing_columns:
                    print(f"⚠️  發現已存在的欄位: {existing_columns}")
                    print("❌ 遷移已經執行過，跳過重複執行")
                    return
                
                print("✅ 欄位檢查完成，開始添加新欄位...")
                
                # 添加新欄位
                migrations = [
                    {
                        'name': 'special_needs_type',
                        'sql': "ALTER TABLE users ADD COLUMN special_needs_type VARCHAR(50) NULL",
                        'description': '驗證類型 (disability/elderly)'
                    },
                    {
                        'name': 'special_needs_document_url', 
                        'sql': "ALTER TABLE users ADD COLUMN special_needs_document_url VARCHAR(500) NULL",
                        'description': '證明文件URL'
                    },
                    {
                        'name': 'special_needs_verified',
                        'sql': "ALTER TABLE users ADD COLUMN special_needs_verified BOOLEAN DEFAULT FALSE",
                        'description': '是否已驗證'
                    },
                    {
                        'name': 'special_needs_applied_at',
                        'sql': "ALTER TABLE users ADD COLUMN special_needs_applied_at TIMESTAMP NULL",
                        'description': '申請時間'
                    }
                ]
                
                # 執行遷移
                for migration in migrations:
                    print(f"📝 添加欄位: {migration['name']} - {migration['description']}")
                    conn.execute(text(migration['sql']))
                    print(f"✅ {migration['name']} 添加成功")
                
                # 提交事務
                trans.commit()
                print("🎉 資料庫遷移完成！")
                
                # 顯示遷移摘要
                print("\n📊 遷移摘要：")
                print("=" * 50)
                print("已添加的欄位：")
                for migration in migrations:
                    print(f"  • {migration['name']}: {migration['description']}")
                
                print("\n💡 使用說明：")
                print("1. 顧客可透過 /customer/special-needs-verification 申請驗證")
                print("2. 管理員可透過後台審核並更新 special_needs_verified 狀態")
                print("3. 驗證類型：'disability'（身心障礙者）或 'elderly'（高齡者）")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ 遷移失敗: {str(e)}")
        print("\n🔧 錯誤排除建議：")
        print("1. 確認資料庫連接設定正確")
        print("2. 檢查資料庫用戶權限")
        print("3. 確認資料表 'users' 存在")
        sys.exit(1)

def rollback_migration():
    """回滾遷移（移除添加的欄位）"""
    print("🔄 開始回滾資料庫遷移...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # 移除欄位（按相反順序）
                rollback_sqls = [
                    "ALTER TABLE users DROP COLUMN IF EXISTS special_needs_applied_at",
                    "ALTER TABLE users DROP COLUMN IF EXISTS special_needs_verified", 
                    "ALTER TABLE users DROP COLUMN IF EXISTS special_needs_document_url",
                    "ALTER TABLE users DROP COLUMN IF EXISTS special_needs_type"
                ]
                
                for sql in rollback_sqls:
                    print(f"📝 執行: {sql}")
                    conn.execute(text(sql))
                
                trans.commit()
                print("✅ 遷移回滾完成")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ 回滾失敗: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="身心障礙者/高齡者驗證功能資料庫遷移")
    parser.add_argument("--rollback", action="store_true", help="回滾遷移")
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
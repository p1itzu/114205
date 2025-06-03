#!/usr/bin/env python3

from database import SessionLocal
from models.order import Order, Negotiation
from sqlalchemy.orm import joinedload

def fix_duplicate_negotiations():
    db = SessionLocal()
    try:
        print("=== 清理重複的議價記錄 ===")
        
        # 獲取訂單4
        order = db.query(Order).options(joinedload(Order.negotiations)).filter(Order.id == 4).first()
        
        if not order:
            print("找不到訂單4")
            return
        
        print(f"訂單: #{order.order_number}")
        print("議價記錄:")
        
        # 顯示所有議價記錄
        for nego in order.negotiations:
            print(f"  ID {nego.id}: {nego.proposed_by} NT${nego.proposed_amount} - {nego.message}")
        
        # 找到重複的廚師最終定價記錄
        chef_final_negotitations = [
            nego for nego in order.negotiations 
            if nego.proposed_by == "chef" and nego.is_accepted is None
        ]
        
        if len(chef_final_negotitations) > 1:
            print(f"\n發現 {len(chef_final_negotitations)} 個重複的廚師最終定價記錄")
            
            # 保留最新的，刪除舊的
            chef_final_negotitations.sort(key=lambda x: x.created_at)
            
            # 刪除除了最後一個之外的所有記錄
            for nego in chef_final_negotitations[:-1]:
                print(f"刪除重複記錄 ID {nego.id}")
                db.delete(nego)
            
            print(f"保留最新記錄 ID {chef_final_negotitations[-1].id}")
            
            db.commit()
            print("✅ 重複記錄已清理")
        else:
            print("沒有發現重複記錄")
        
        # 顯示清理後的結果
        print("\n=== 清理後的議價記錄 ===")
        db.refresh(order)
        for nego in order.negotiations:
            status = '已接受' if nego.is_accepted == True else '已拒絕' if nego.is_accepted == False else '待回應'
            print(f"  {nego.proposed_by}: NT${nego.proposed_amount} ({status}) - {nego.message or '無說明'}")
            
    except Exception as e:
        print(f"錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_duplicate_negotiations() 
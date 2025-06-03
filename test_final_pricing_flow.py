#!/usr/bin/env python3
"""
測試最終定價流程
1. 廚師提交最終定價
2. 顧客查看並回應最終定價
3. 訂單狀態更新
"""

from database import SessionLocal
from models.order import Order, OrderStatus, Negotiation
from sqlalchemy.orm import joinedload
from datetime import datetime

def test_final_pricing_flow():
    db = SessionLocal()
    
    try:
        # 1. 創建測試訂單和議價記錄
        print("=== 創建測試訂單 ===")
        
        # 查找已有的議價中訂單
        order = db.query(Order).options(
            joinedload(Order.negotiations)
        ).filter(Order.status == OrderStatus.NEGOTIATING).first()
        
        if not order:
            print("沒有找到議價中的訂單，請先創建測試數據")
            return
            
        print(f"使用訂單：#{order.order_number} (ID: {order.id})")
        
        # 檢查是否已有顧客議價記錄
        customer_nego = None
        for nego in order.negotiations:
            if nego.proposed_by == "customer" and nego.is_accepted is None:
                customer_nego = nego
                break
        
        if not customer_nego:
            # 創建顧客議價記錄
            customer_nego = Negotiation(
                order_id=order.id,
                proposed_amount=800,
                proposed_by="customer",
                message="希望能便宜一點",
                created_at=datetime.utcnow()
            )
            db.add(customer_nego)
            db.commit()
            db.refresh(customer_nego)
            print(f"創建顧客議價記錄：NT$800")
        else:
            print(f"使用現有顧客議價：NT${customer_nego.proposed_amount}")
        
        # 2. 模擬廚師提交最終定價
        print("\n=== 廚師提交最終定價 ===")
        
        # 檢查是否已有廚師最終定價
        chef_final_pricing = None
        for nego in order.negotiations:
            if nego.proposed_by == "chef" and nego.is_accepted is None:
                chef_final_pricing = nego
                break
        
        if not chef_final_pricing:
            # 創建廚師最終定價記錄
            final_amount = 900
            chef_final_pricing = Negotiation(
                order_id=order.id,
                proposed_amount=final_amount,
                proposed_by="chef",
                message="考慮成本後的最終定價",
                created_at=datetime.utcnow()
            )
            db.add(chef_final_pricing)
            db.commit()
            db.refresh(chef_final_pricing)
            print(f"廚師提交最終定價：NT${final_amount}")
        else:
            final_amount = chef_final_pricing.proposed_amount
            print(f"使用現有廚師最終定價：NT${final_amount}")
        
        # 更新訂單總價
        order.total_amount = final_amount
        db.commit()
        
        # 3. 顯示當前狀態
        print(f"\n=== 當前狀態 ===")
        print(f"訂單狀態：NEGOTIATING (等待顧客回應最終定價)")
        print(f"顧客議價：NT${customer_nego.proposed_amount}")
        print(f"廚師最終定價：NT${final_amount}")
        print(f"廚師議價記錄ID：{chef_final_pricing.id}")
        
        # 4. 測試顧客回應選項
        print(f"\n=== 測試說明 ===")
        print(f"現在顧客可以：")
        print(f"1. 訪問 /customer/order/{order.id}/final_pricing 查看最終定價")
        print(f"2. 選擇接受 → 訂單狀態變成 ACCEPTED")
        print(f"3. 選擇拒絕 → 訂單狀態變成 CANCELLED")
        print(f"\n測試API端點：")
        print(f"POST /customer/order/{order.id}/respond_final_pricing/{chef_final_pricing.id}")
        print(f"Body: {{\"is_accepted\": true}} 或 {{\"is_accepted\": false}}")
        
        print(f"\n✅ 測試環境設置完成！")
        
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_final_pricing_flow() 
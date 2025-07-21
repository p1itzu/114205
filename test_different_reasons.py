#!/usr/bin/env python3
"""
測試不同原因的重新選擇廚師情況
"""

from database import SessionLocal
from models.user import User, UserRole
from models.order import Order, OrderStatus, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel, OrderStatusHistory
from datetime import datetime
import uuid

def test_different_reasons():
    db = SessionLocal()
    
    try:
        print("=== 測試不同原因的重新選擇廚師情況 ===")
        
        # 1. 尋找現有的訂單並更新為不同原因
        orders = db.query(Order).filter(Order.status == OrderStatus.CANCELLED).all()
        
        if not orders:
            print("沒有找到已取消的訂單")
            return
        
        print(f"找到 {len(orders)} 個已取消的訂單")
        
        # 2. 將不同的訂單設置為不同的原因
        reasons = [
            ("廚師拒絕接單", "廚師拒絕接單，顧客可重新選擇廚師"),
            ("議價失敗", "議價次數用盡，顧客可重新選擇廚師"),
            ("其他原因", "系統更新：從已取消變更為重新選擇廚師")
        ]
        
        for i, order in enumerate(orders):
            reason_type, reason_note = reasons[i % len(reasons)]
            
            print(f"\n更新訂單 {order.id} - 原因: {reason_type}")
            
            # 更新訂單狀態
            old_status = order.status
            order.status = OrderStatus.RESELECTING_CHEF
            order.chef_id = None
            
            # 創建狀態歷史記錄
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status=OrderStatus.RESELECTING_CHEF,
                notes=reason_note
            )
            db.add(status_history)
            
            print(f"  狀態: {old_status.value} → {order.status.value}")
            print(f"  原因: {reason_note}")
        
        # 3. 提交更改
        db.commit()
        print(f"\n✅ 成功更新 {len(orders)} 個訂單")
        
        # 4. 驗證結果
        print("\n=== 驗證結果 ===")
        reselecting_orders = db.query(Order).filter(
            Order.status == OrderStatus.RESELECTING_CHEF
        ).all()
        
        for order in reselecting_orders:
            latest_history = db.query(OrderStatusHistory).filter(
                OrderStatusHistory.order_id == order.id,
                OrderStatusHistory.new_status == OrderStatus.RESELECTING_CHEF
            ).order_by(OrderStatusHistory.created_at.desc()).first()
            
            # 判斷原因
            reason = "其他原因"
            if latest_history and latest_history.notes:
                if "拒絕接單" in latest_history.notes:
                    reason = "廚師拒絕接單"
                elif "議價失敗" in latest_history.notes or "議價次數用盡" in latest_history.notes:
                    reason = "議價失敗"
            
            print(f"訂單 {order.id}: {order.order_number}")
            print(f"  狀態: {order.status.value}")
            print(f"  判斷原因: {reason}")
            print(f"  歷史記錄: {latest_history.notes if latest_history else 'None'}")
            print("---")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_different_reasons() 
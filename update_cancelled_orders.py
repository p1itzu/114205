#!/usr/bin/env python3
"""
更新已取消的訂單狀態為重新選擇廚師
"""

from database import SessionLocal
from models.order import Order, OrderStatus, OrderStatusHistory
from datetime import datetime

def update_cancelled_orders():
    db = SessionLocal()
    
    try:
        print("=== 更新已取消的訂單狀態 ===")
        
        # 查找所有已取消的訂單
        cancelled_orders = db.query(Order).filter(
            Order.status == OrderStatus.CANCELLED
        ).all()
        
        if not cancelled_orders:
            print("沒有找到已取消的訂單")
            return
        
        print(f"找到 {len(cancelled_orders)} 個已取消的訂單")
        
        for order in cancelled_orders:
            print(f"\n更新訂單 {order.id} ({order.order_number})")
            print(f"  目前狀態: {order.status.value}")
            
            # 更新狀態為重新選擇廚師
            old_status = order.status
            order.status = OrderStatus.RESELECTING_CHEF
            order.chef_id = None  # 清除廚師分配
            
            # 記錄狀態歷史
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status=OrderStatus.RESELECTING_CHEF,
                notes="系統更新：從已取消變更為重新選擇廚師"
            )
            db.add(status_history)
            
            print(f"  新狀態: {order.status.value}")
            print(f"  廚師ID已清除: {order.chef_id}")
        
        # 提交所有更改
        db.commit()
        print(f"\n✅ 成功更新 {len(cancelled_orders)} 個訂單的狀態")
        
        # 驗證更新結果
        print("\n=== 驗證更新結果 ===")
        reselecting_orders = db.query(Order).filter(
            Order.status == OrderStatus.RESELECTING_CHEF
        ).all()
        
        print(f"現在有 {len(reselecting_orders)} 個訂單處於重新選擇廚師狀態")
        
        for order in reselecting_orders:
            print(f"  訂單 {order.id}: {order.order_number} - {order.status.value}")
        
    except Exception as e:
        print(f"更新失敗: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_cancelled_orders() 
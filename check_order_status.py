#!/usr/bin/env python3
"""
檢查數據庫中的訂單狀態
"""

from database import SessionLocal
from models.order import Order, OrderStatus

def check_order_status():
    db = SessionLocal()
    try:
        orders = db.query(Order).all()
        print(f"總共找到 {len(orders)} 個訂單:")
        
        for order in orders:
            print(f"訂單 ID: {order.id}")
            print(f"  狀態對象: {order.status}")
            print(f"  狀態類型: {type(order.status)}")
            
            if order.status:
                print(f"  狀態值: {order.status.value}")
                print(f"  狀態名稱: {order.status.name}")
            else:
                print(f"  狀態值: None")
            
            print("---")
            
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_order_status() 
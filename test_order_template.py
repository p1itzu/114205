#!/usr/bin/env python3
"""
測試訂單列表模板的HTML輸出
"""

from database import SessionLocal
from models.order import Order
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import joinedload

def test_order_template():
    # 設置 Jinja2 環境
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('order_list.html')
    
    # 從數據庫獲取訂單
    db = SessionLocal()
    try:
        orders = db.query(Order).options(
            joinedload(Order.dishes)
        ).all()
        
        print(f"找到 {len(orders)} 個訂單")
        
        for order in orders:
            print(f"\n訂單 {order.id} 的狀態信息:")
            print(f"  order.status = {order.status}")
            print(f"  order.status.value = {order.status.value}")
            print(f"  order.status.name = {order.status.name}")
            
            # 測試模板條件
            status_text = ""
            if order.status.value == 'pending':
                status_text = "等待回應"
            elif order.status.value == 'accepted':
                status_text = "已接單"
            elif order.status.value == 'preparing':
                status_text = "製作中"
            elif order.status.value == 'ready':
                status_text = "製作完成"
            elif order.status.value == 'delivering':
                status_text = "配送中"
            elif order.status.value == 'completed':
                status_text = "交付完成"
            elif order.status.value == 'cancelled':
                status_text = "已取消"
            else:
                status_text = order.status.value
                
            print(f"  應該顯示的狀態文字: {status_text}")
            
            # 生成狀態HTML片段
            status_html = f'<span class="status {order.status.value}">{status_text}</span>'
            print(f"  狀態HTML: {status_html}")
            
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_order_template() 
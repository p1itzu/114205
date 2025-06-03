#!/usr/bin/env python3

from database import SessionLocal
from models.order import Order, Negotiation
from sqlalchemy.orm import joinedload

def check_order_4():
    db = SessionLocal()
    try:
        order = db.query(Order).options(joinedload(Order.negotiations)).filter(Order.id == 4).first()
        
        if order:
            print(f'訂單: #{order.order_number}')
            print(f'狀態: {order.status.value}')
            print(f'總金額: NT${order.total_amount}')
            print('')
            print('議價記錄:')
            for nego in order.negotiations:
                status = '已接受' if nego.is_accepted == True else '已拒絕' if nego.is_accepted == False else '待回應'
                print(f'  {nego.proposed_by}: NT${nego.proposed_amount} ({status}) - {nego.message or "無說明"}')
        else:
            print('找不到訂單 ID 4')
    finally:
        db.close()

if __name__ == "__main__":
    check_order_4() 
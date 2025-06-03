from sqlalchemy.orm import Session
from database import SessionLocal
from models.order import Order, Negotiation
from datetime import datetime

def check_negotiation_status():
    db = SessionLocal()
    
    try:
        print("=== 檢查議價中的訂單 ===")
        
        # 使用ORM查詢議價中的訂單
        orders = db.query(Order).filter(Order.status == 'negotiating').all()
        
        if not orders:
            print("沒有找到議價中的訂單")
            return
        
        for order in orders:
            print(f"訂單ID: {order.id}, 編號: {order.order_number}, 狀態: {order.status}, 廚師ID: {order.chef_id}, 金額: {order.total_amount}")
        
        print("\n=== 檢查議價記錄 ===")
        
        # 查詢所有議價記錄
        negotiations = db.query(Negotiation).join(Order).filter(Order.status == 'negotiating').all()
        
        if not negotiations:
            print("沒有找到議價記錄")
        else:
            for nego in negotiations:
                print(f"議價ID: {nego.id}, 訂單ID: {nego.order_id}, 提議方: {nego.proposed_by}, 金額: {nego.proposed_amount}, 是否接受: {nego.is_accepted}, 訊息: {nego.message}")
        
        print("\n=== 檢查是否有待回應的顧客議價 ===")
        
        # 查詢待回應的顧客議價
        customer_offers = db.query(Negotiation).join(Order).filter(
            Order.status == 'negotiating',
            Negotiation.proposed_by == 'customer',
            Negotiation.is_accepted.is_(None)
        ).all()
        
        if not customer_offers:
            print("沒有找到待回應的顧客議價")
        else:
            for offer in customer_offers:
                print(f"訂單ID: {offer.order_id}, 議價ID: {offer.id}, 提議方: {offer.proposed_by}, 金額: {offer.proposed_amount}, 狀態: {offer.is_accepted}")
                
                # 檢查這個訂單的詳細信息
                order = db.query(Order).filter(Order.id == offer.order_id).first()
                if order:
                    print(f"  -> 訂單編號: {order.order_number}, 廚師ID: {order.chef_id}")
    
    except Exception as e:
        print(f"查詢時發生錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_negotiation_status() 
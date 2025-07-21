#!/usr/bin/env python3
"""
測試重新選擇廚師功能
"""

from database import SessionLocal
from models.user import User, UserRole
from models.order import Order, OrderStatus, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel, OrderStatusHistory
from models.chef import ChefProfile
from datetime import datetime
import uuid

def test_reselect_chef_flow():
    db = SessionLocal()
    
    try:
        print("=== 測試重新選擇廚師流程 ===")
        
        # 1. 尋找或創建顧客
        customer = db.query(User).filter(User.role == UserRole.CUSTOMER).first()
        if not customer:
            print("沒有找到顧客，請先運行 init_sample_data.py")
            return
        
        # 2. 尋找或創建廚師
        chef = db.query(User).filter(User.role == UserRole.CHEF).first()
        if not chef:
            print("沒有找到廚師，請先運行 init_sample_data.py")
            return
        
        print(f"使用顧客: {customer.name} ({customer.email})")
        print(f"使用廚師: {chef.name} ({chef.email})")
        
        # 3. 創建測試訂單
        test_order = Order(
            customer_id=customer.id,
            chef_id=chef.id,
            order_number=f"TEST{uuid.uuid4().hex[:6].upper()}",
            status=OrderStatus.PENDING,
            delivery_method=DeliveryMethod.PICKUP,
            delivery_address="測試地址",
            total_amount=300.0,
            customer_notes="測試重新選擇廚師功能"
        )
        db.add(test_order)
        db.commit()
        db.refresh(test_order)
        
        print(f"\n創建測試訂單: {test_order.order_number} (ID: {test_order.id})")
        
        # 4. 添加測試菜品
        test_dish = OrderDish(
            order_id=test_order.id,
            dish_name="測試菜品",
            quantity=1,
            unit_price=0,
            salt_level=SaltLevel.NORMAL,
            spice_level=SpiceLevel.NONE
        )
        db.add(test_dish)
        db.commit()
        
        # 5. 模擬廚師拒絕接單
        print("\n=== 模擬廚師拒絕接單 ===")
        old_status = test_order.status
        test_order.status = OrderStatus.RESELECTING_CHEF
        test_order.chef_id = None  # 清除廚師分配
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=test_order.id,
            old_status=old_status,
            new_status=OrderStatus.RESELECTING_CHEF,
            notes=f"測試：廚師拒絕接單，顧客可重新選擇廚師"
        )
        db.add(status_history)
        db.commit()
        
        print(f"訂單狀態從 {old_status.value} 變更為 {test_order.status.value}")
        print(f"廚師分配已清除: {test_order.chef_id}")
        
        # 6. 驗證狀態
        print("\n=== 驗證訂單狀態 ===")
        updated_order = db.query(Order).filter(Order.id == test_order.id).first()
        print(f"訂單ID: {updated_order.id}")
        print(f"狀態: {updated_order.status.value}")
        print(f"廚師ID: {updated_order.chef_id}")
        
        # 7. 模擬重新選擇廚師
        print("\n=== 模擬重新選擇廚師 ===")
        
        # 尋找另一個廚師
        new_chef = db.query(User).filter(
            User.role == UserRole.CHEF,
            User.id != chef.id
        ).first()
        
        if not new_chef:
            # 如果沒有其他廚師，就用原來的廚師
            new_chef = chef
            print("沒有其他廚師，使用原來的廚師")
        
        # 重新分配廚師
        old_status = updated_order.status
        updated_order.chef_id = new_chef.id
        updated_order.status = OrderStatus.PENDING
        updated_order.negotiation_count = 0  # 重置議價次數
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=updated_order.id,
            old_status=old_status,
            new_status=OrderStatus.PENDING,
            notes=f"測試：顧客重新選擇廚師：{new_chef.name}"
        )
        db.add(status_history)
        db.commit()
        
        print(f"重新分配廚師: {new_chef.name} ({new_chef.email})")
        print(f"訂單狀態從 {old_status.value} 變更為 {updated_order.status.value}")
        
        # 8. 最終驗證
        print("\n=== 最終驗證 ===")
        final_order = db.query(Order).filter(Order.id == updated_order.id).first()
        print(f"訂單ID: {final_order.id}")
        print(f"訂單編號: {final_order.order_number}")
        print(f"狀態: {final_order.status.value}")
        print(f"廚師ID: {final_order.chef_id}")
        print(f"廚師名稱: {new_chef.name}")
        
        # 9. 顯示狀態歷史
        print("\n=== 狀態歷史 ===")
        histories = db.query(OrderStatusHistory).filter(
            OrderStatusHistory.order_id == final_order.id
        ).order_by(OrderStatusHistory.created_at).all()
        
        for history in histories:
            print(f"時間: {history.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  {history.old_status.value if history.old_status else 'None'} → {history.new_status.value}")
            print(f"  備註: {history.notes}")
            print("---")
        
        print(f"\n✅ 測試完成！訂單 {final_order.order_number} 現在處於 {final_order.status.value} 狀態")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_reselect_chef_flow() 
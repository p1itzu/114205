from fastapi import APIRouter, Request, Depends, HTTPException, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid

from database import get_db
from models.order import Order, OrderStatus, OrderStatusHistory, Negotiation, OrderDish
from models.user import User
from models.chef import ChefProfile, ChefSpecialty, ChefSignatureDish
from models.message import Message
from utils.dependencies import require_chef, common_template_params

router = APIRouter(dependencies=[Depends(require_chef)])
templates = Jinja2Templates(directory="templates")

class RejectOrderRequest(BaseModel):
    reason: str

class NegotiationRequest(BaseModel):
    proposed_amount: float
    message: Optional[str] = None

@router.get("/", name="chef_dashboard")
def chef_dashboard(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取分配給當前廚師且狀態為 PENDING 的訂單（待廚師接單）
    pending_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status == OrderStatus.PENDING
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # 獲取廚師已接的訂單
    my_orders = db.query(Order).filter(
        Order.chef_id == current_user.id
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        "chef_dashboard.html",
        {
            **commons,
            "current_user": current_user,
            "pending_orders": pending_orders,
            "my_orders": my_orders
        }
    )

@router.get("/pending-orders", name="chef_pending_orders")
def chef_pending_orders(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取分配給當前廚師且狀態為 PENDING 的訂單（待廚師接單）
    pending_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status == OrderStatus.PENDING
    ).order_by(Order.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "chef_pending_orders.html",
        {
            **commons,
            "current_user": current_user,
            "pending_orders": pending_orders
        }
    )

@router.get("/order/{order_id}", name="chef_order_detail")
def chef_order_detail(
    order_id: int,
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    from sqlalchemy.orm import joinedload
    
    # 獲取訂單詳情，包含negotiations關聯
    order = db.query(Order).options(
        joinedload(Order.negotiations),
        joinedload(Order.dishes),
        joinedload(Order.customer)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # 檢查權限：只有被分配此訂單的廚師可以查看，或者是取消的訂單（chef_id可能為None）
    if order.chef_id is not None and order.chef_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權查看此訂單")
    
    return templates.TemplateResponse(
        "chef_order_detail.html",
        {
            **commons,
            "current_user": current_user,
            "order": order
        }
    )

@router.post("/order/{order_id}/accept")
def accept_order(
    order_id: int,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).options(
        joinedload(Order.negotiations),
        joinedload(Order.dishes),
        joinedload(Order.customer)
    ).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.PENDING:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單無法接單"}
        )
    
    # 檢查訂單是否已分配給當前廚師，或者未分配（可自動分配）
    if order.chef_id is not None and order.chef_id != current_user.id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單已被其他廚師接單"}
        )
    
    try:
        # 記錄原始狀態
        old_status = order.status
        
        # 自動分配廚師（如果未分配）
        if order.chef_id is None:
            order.chef_id = current_user.id
        
        # 更新訂單狀態為議價中
        order.status = OrderStatus.NEGOTIATING
        order.accepted_at = datetime.utcnow()
        order.negotiation_count = 0
        
        # 記錄原始金額
        order.original_amount = order.total_amount
        
        # 記錄狀態變更歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.NEGOTIATING,
            notes=f"廚師 {current_user.email} 接單，進入議價階段"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={
                "success": True, 
                "message": "接單成功！",
                "redirect_url": f"/chef/order/{order_id}/pricing"
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"系統錯誤：{str(e)}"}
        )

@router.post("/order/{order_id}/reject")
def reject_order(
    order_id: int,
    reject_data: RejectOrderRequest,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.PENDING:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單無法拒絕"}
        )
    
    # 檢查訂單是否分配給當前廚師
    if order.chef_id is not None and order.chef_id != current_user.id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單未分配給您"}
        )
    
    try:
        # 記錄拒絕原因到狀態歷史，並將訂單狀態改為取消
        old_status = order.status
        order.status = OrderStatus.CANCELLED
        order.chef_id = None  # 清除廚師分配，讓其他廚師可以接單
        
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.CANCELLED,
            notes=f"廚師 {current_user.email} 拒絕接單，原因：{reject_data.reason}"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "拒絕成功"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "系統錯誤，請稍後再試"}
        )

@router.get("/accepted-orders", name="chef_accepted_orders")
def chef_accepted_orders(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取廚師已接的訂單（待完成）
    accepted_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.PREPARING])
    ).order_by(Order.accepted_at.desc()).all()
    
    return templates.TemplateResponse(
        "chef_accepted_orders.html",
        {
            **commons,
            "current_user": current_user,
            "accepted_orders": accepted_orders
        }
    )

@router.get("/completed-orders", name="chef_completed_orders")
def chef_completed_orders(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取廚師已完成的訂單
    completed_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status == OrderStatus.COMPLETED
    ).order_by(Order.completed_at.desc()).all()
    
    return templates.TemplateResponse(
        "chef_completed_orders.html",
        {
            **commons,
            "current_user": current_user,
            "completed_orders": completed_orders
        }
    )

@router.get("/negotiating-orders", name="chef_negotiating_orders")
def chef_negotiating_orders(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取議價中的訂單（這裡可以根據需要擴展狀態）
    negotiating_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status == OrderStatus.PREPARING  # 暫時用準備中狀態代表議價中
    ).order_by(Order.accepted_at.desc()).all()
    
    return templates.TemplateResponse(
        "chef_negotiating_orders.html",
        {
            **commons,
            "current_user": current_user,
            "negotiating_orders": negotiating_orders
        }
    )

@router.get("/cancelled-orders", name="chef_cancelled_orders")
def chef_cancelled_orders(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取已取消的訂單
    cancelled_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.status == OrderStatus.CANCELLED
    ).order_by(Order.updated_at.desc()).all()
    
    return templates.TemplateResponse(
        "chef_cancelled_orders.html",
        {
            **commons,
            "current_user": current_user,
            "cancelled_orders": cancelled_orders
        }
    )

# 暫時用這個路由名稱來兼容模板
@router.get("/profile", name="chef_profile")
def chef_profile(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        "chef_profile.html",
        {
            **commons,
            "current_user": current_user
        }
    )

# 廚師主頁 - 用戶提供的頁面
@router.get("/main", name="chef_main")
def chef_main(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取廚師詳細資料
    chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == current_user.id).first()
    
    # 獲取專長
    chef_specialties = []
    signature_dishes = []
    
    if chef_profile:
        chef_specialties = db.query(ChefSpecialty).filter(ChefSpecialty.chef_id == chef_profile.id).all()
        signature_dishes = db.query(ChefSignatureDish).filter(ChefSignatureDish.chef_id == chef_profile.id).all()
    
    # 獲取最新通知
    notifications = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).order_by(Message.created_at.desc()).limit(8).all()
    
    # 獲取今日訂單
    today = datetime.now().date()
    recent_orders = db.query(Order).filter(
        Order.chef_id == current_user.id,
        Order.created_at >= today
    ).order_by(Order.created_at.desc()).limit(3).all()
    
    return templates.TemplateResponse(
        "chef_main.html",
        {
            **commons,
            "current_user": current_user,
            "chef_profile": chef_profile or ChefProfile(),  # 如果沒有資料就用空物件
            "chef_specialties": chef_specialties,
            "signature_dishes": signature_dishes,
            "notifications": notifications,
            "recent_orders": recent_orders
        }
    )

# 更新廚師個人資料
@router.post("/profile/update")
async def update_chef_profile(
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    kitchen_address: Optional[str] = Form(None),
    certificate_name: Optional[str] = Form(None),
    specialties: Optional[str] = Form(None),
    experience_years: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    certificate_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    try:
        # 更新用戶基本資料
        current_user.name = name
        if phone:
            current_user.phone = phone
        
        # 處理頭像上傳
        if photo:
            # 確保uploads目錄存在
            os.makedirs("static/uploads/avatars", exist_ok=True)
            
            # 生成唯一檔名
            file_extension = photo.filename.split('.')[-1] if '.' in photo.filename else 'jpg'
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"static/uploads/avatars/{filename}"
            
            # 儲存檔案
            with open(file_path, "wb") as buffer:
                content = await photo.read()
                buffer.write(content)
            
            current_user.avatar_url = f"/static/uploads/avatars/{filename}"
        
        # 獲取或創建廚師資料
        chef_profile = db.query(ChefProfile).filter(ChefProfile.user_id == current_user.id).first()
        if not chef_profile:
            chef_profile = ChefProfile(user_id=current_user.id)
            db.add(chef_profile)
            db.flush()  # 獲取ID但不提交
        
        # 更新廚師資料
        if kitchen_address:
            chef_profile.kitchen_address = kitchen_address
        if certificate_name:
            chef_profile.certificate_name = certificate_name
        if experience_years:
            chef_profile.experience_years = experience_years
        if description:
            chef_profile.description = description
        
        # 處理證照上傳
        if certificate_photo:
            os.makedirs("static/uploads/certificates", exist_ok=True)
            
            file_extension = certificate_photo.filename.split('.')[-1] if '.' in certificate_photo.filename else 'jpg'
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"static/uploads/certificates/{filename}"
            
            with open(file_path, "wb") as buffer:
                content = await certificate_photo.read()
                buffer.write(content)
            
            chef_profile.certificate_image_url = f"/static/uploads/certificates/{filename}"
            chef_profile.certificate_verified = False  # 需要重新審核
        
        # 更新專長
        if specialties:
            # 刪除現有專長
            db.query(ChefSpecialty).filter(ChefSpecialty.chef_id == chef_profile.id).delete()
            
            # 添加新專長
            specialty_list = [s.strip() for s in specialties.split(',') if s.strip()]
            for specialty in specialty_list:
                new_specialty = ChefSpecialty(
                    chef_id=chef_profile.id,
                    specialty=specialty
                )
                db.add(new_specialty)
        
        db.commit()
        
        return JSONResponse(content={"success": True, "message": "個人資料更新成功！"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"更新失敗：{str(e)}"}
        )

# 廚師提出議價
@router.post("/order/{order_id}/negotiate")
def chef_negotiate(
    order_id: int,
    negotiation_data: NegotiationRequest,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查權限
    if order.chef_id != current_user.id:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "無權操作此訂單"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.NEGOTIATING:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單目前無法議價"}
        )
    
    # 檢查議價次數
    if order.negotiation_count >= 2:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "已達最大議價次數"}
        )
    
    try:
        # 創建議價記錄
        negotiation = Negotiation(
            order_id=order.id,
            proposed_amount=negotiation_data.proposed_amount,
            proposed_by="chef",
            message=negotiation_data.message
        )
        db.add(negotiation)
        
        # 更新訂單議價信息
        order.negotiated_amount = negotiation_data.proposed_amount
        order.negotiation_count += 1
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=OrderStatus.NEGOTIATING,
            new_status=OrderStatus.NEGOTIATING,
            notes=f"廚師提出議價：NT${negotiation_data.proposed_amount}"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "議價提案已送出"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"議價失敗：{str(e)}"}
        )

# 確認議價完成，進入正式接單
@router.post("/order/{order_id}/confirm_negotiation")
def confirm_negotiation(
    order_id: int,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查權限
    if order.chef_id != current_user.id:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "無權操作此訂單"}
        )
    
    # 檢查是否有被接受的議價
    accepted_negotiation = db.query(Negotiation).filter(
        Negotiation.order_id == order.id,
        Negotiation.is_accepted == True
    ).first()
    
    if not accepted_negotiation:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "沒有被接受的議價"}
        )
    
    try:
        # 更新訂單狀態為已接單
        old_status = order.status
        order.status = OrderStatus.ACCEPTED
        order.total_amount = accepted_negotiation.proposed_amount
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.ACCEPTED,
            notes=f"議價完成，正式接單，金額：NT${accepted_negotiation.proposed_amount}"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "議價完成，訂單正式開始"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"確認失敗：{str(e)}"}
        )

# 廚師估價頁面
@router.get("/order/{order_id}/pricing")
def chef_pricing_page(
    order_id: int,
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).options(
        joinedload(Order.dishes),
        joinedload(Order.customer)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # 檢查權限
    if order.chef_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權操作此訂單")
    
    # 檢查訂單狀態
    if order.status != OrderStatus.NEGOTIATING:
        raise HTTPException(status_code=400, detail="此訂單不在議價狀態")
    
    return templates.TemplateResponse(
        "chef_pricing.html",
        {
            **commons,
            "request": request,
            "order": order,
            "current_user": current_user
        }
    )

class PricingSubmission(BaseModel):
    dish_prices: List[dict]
    total_amount: float
    pricing_notes: Optional[str] = None

# 提交估價
@router.post("/order/{order_id}/submit_pricing")
def submit_pricing(
    order_id: int,
    pricing_data: PricingSubmission,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).options(
        joinedload(Order.dishes)
    ).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查權限
    if order.chef_id != current_user.id:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "無權操作此訂單"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.NEGOTIATING:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單不在議價狀態"}
        )
    
    try:
        # 更新菜品價格
        for dish_price_data in pricing_data.dish_prices:
            dish_id = dish_price_data["dish_id"]
            price = dish_price_data["price"]
            
            dish = db.query(OrderDish).filter(
                OrderDish.id == dish_id,
                OrderDish.order_id == order_id
            ).first()
            
            if dish:
                dish.unit_price = price
        
        # 更新訂單總金額
        order.total_amount = pricing_data.total_amount
        
        # 創建議價記錄
        negotiation = Negotiation(
            order_id=order.id,
            proposed_amount=pricing_data.total_amount,
            proposed_by="chef",
            message=pricing_data.pricing_notes,
            created_at=datetime.utcnow()
        )
        db.add(negotiation)
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=OrderStatus.NEGOTIATING,
            new_status=OrderStatus.NEGOTIATING,
            notes=f"廚師提交估價：NT${pricing_data.total_amount}"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "估價已提交，等待顧客回應"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"提交失敗：{str(e)}"}
        )

# 處理顧客再議價
@router.post("/order/{order_id}/respond_counter_offer/{negotiation_id}")
def respond_counter_offer(
    order_id: int,
    negotiation_id: int,
    response_data: dict,
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查權限
    if order.chef_id != current_user.id:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "無權操作此訂單"}
        )
    
    # 獲取顧客的議價記錄
    negotiation = db.query(Negotiation).filter(
        Negotiation.id == negotiation_id,
        Negotiation.order_id == order_id,
        Negotiation.proposed_by == "customer"  # 確保是顧客發起的議價
    ).first()
    
    if not negotiation:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "議價記錄不存在"}
        )
    
    try:
        is_accepted = response_data.get('is_accepted', False)
        
        # 更新議價記錄
        negotiation.is_accepted = is_accepted
        negotiation.responded_at = datetime.utcnow()
        
        if is_accepted:
            # 廚師接受顧客的再議價
            order.status = OrderStatus.ACCEPTED
            order.total_amount = negotiation.proposed_amount
            
            # 更新菜品價格（按比例分配）
            total_current = sum(dish.unit_price for dish in order.dishes)
            if total_current > 0:
                ratio = negotiation.proposed_amount / total_current
                for dish in order.dishes:
                    dish.unit_price = dish.unit_price * ratio
            
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=OrderStatus.NEGOTIATING,
                new_status=OrderStatus.ACCEPTED,
                notes=f"廚師接受顧客再議價：NT${negotiation.proposed_amount}"
            )
            message = "已接受顧客議價，訂單確認成功！"
            
        else:
            # 廚師拒絕顧客的再議價，訂單取消
            order.status = OrderStatus.CANCELLED
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=OrderStatus.NEGOTIATING,
                new_status=OrderStatus.CANCELLED,
                notes=f"廚師拒絕顧客再議價，訂單取消"
            )
            message = "已拒絕顧客議價，訂單取消"
        
        db.add(status_history)
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": message}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"操作失敗：{str(e)}"}
        )
    

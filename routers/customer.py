from fastapi import APIRouter, Request, Form, HTTPException, Depends, status, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import os
import shutil
import openai
import whisper
import tempfile

from database import get_db
from models.user import User
from models.order import Order, OrderStatus, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel, Negotiation, OrderStatusHistory
from models.review import Review
from models.chef import ChefProfile, ChefSignatureDish, ChefSpecialty
from models.notification import Notification, NotificationType
from routers.notification import create_notification
from utils.dependencies import require_customer, common_template_params
from utils.security import get_password_hash, verify_password
from pydantic import BaseModel

router = APIRouter(dependencies=[Depends(require_customer)])
templates = Jinja2Templates(directory="templates")

# 料理方式建議頁面
@router.get("/cooking_method", name="cooking_method")
def cooking_method(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse("cooking_method.html", {
        **commons,
        "request": request,
        "user": current_user
    })

class NegotiationResponse(BaseModel):
    is_accepted: bool
    response_message: Optional[str] = None
    counter_amount: Optional[float] = None

class ReviewRequest(BaseModel):
    rating: int
    content: Optional[str] = None

class VoiceOrderRequest(BaseModel):
    message: str
    order_data: dict

class VoiceOrderData(BaseModel):
    chef_id: int
    chef_name: str
    order_date: Optional[str] = None
    order_time: Optional[str] = None
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None
    dishes: List[dict] = []
    customer_notes: str = ""

# 廚師詳細資料頁面
@router.get("/chef/{chef_id}/profile")
def chef_profile_page(
    chef_id: int,
    request: Request,
    commons=Depends(common_template_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """廚師詳細資料頁面"""
    # 查詢廚師基本資料
    chef = db.query(User).filter(
        User.id == chef_id,
        User.role == "chef"
    ).first()
    
    if not chef:
        raise HTTPException(status_code=404, detail="廚師不存在")
    
    # 查詢廚師評價（最新10則）
    reviews = db.query(Review).filter(
        Review.reviewee_id == chef_id
    ).order_by(Review.created_at.desc()).limit(10).all()
    
    # 查詢招牌菜（通過 chef_profile.id）
    signature_dishes = []
    if chef.chef_profile:
        signature_dishes = db.query(ChefSignatureDish).filter(
            ChefSignatureDish.chef_id == chef.chef_profile.id
        ).all()
    
    # 查詢專長
    specialties = []
    if chef.chef_profile:
        specialties = db.query(ChefSpecialty).filter(
            ChefSpecialty.chef_id == chef.chef_profile.id
        ).all()
    
    # 計算已完成訂單數
    completed_orders_count = db.query(Order).filter(
        Order.chef_id == chef_id,
        Order.status == OrderStatus.COMPLETED
    ).count()
    
    # 計算評價統計
    review_stats = {}
    if reviews:
        total_reviews = len(reviews)
        for i in range(1, 6):
            count = len([r for r in reviews if r.rating == i])
            review_stats[i] = count
    else:
        review_stats = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_reviews = 0
    
    return templates.TemplateResponse("chef_profile.html", {
        **commons,
        "request": request,
        "chef": chef,
        "reviews": reviews,
        "signature_dishes": signature_dishes,
        "specialties": specialties,
        "completed_orders_count": completed_orders_count,
        "review_stats": review_stats,
        "total_reviews": total_reviews
    })

# 訂單列表
@router.get("/orders/list", name="customer_order_list")
def order_list_page(
    request: Request,
    commons=Depends(common_template_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    from sqlalchemy.orm import joinedload
    
    orders = db.query(Order).options(
        joinedload(Order.dishes),
        joinedload(Order.negotiations)
    ).filter(Order.customer_id == current_user.id).order_by(Order.created_at.desc()).all()
    
    return templates.TemplateResponse("order_list.html", {**commons, "request": request, "user": current_user, "orders": orders})

# 訂單詳情
@router.get("/order/{order_id}", name="order_detail")
def order_detail(
    order_id: int, 
    request: Request, 
    commons=Depends(common_template_params), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    from sqlalchemy.orm import joinedload
    
    order = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.dishes),
        joinedload(Order.negotiations)
    ).filter(
        Order.id == order_id, 
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # 檢查是否有待顧客回應的廚師定價
    chef_final_pricing_pending = False
    chef_final_pricing = None
    is_final_round = False  # 是否為最終議價階段
    
    # 檢查是否有顧客的反議價記錄
    customer_negotiations = [n for n in order.negotiations if n.proposed_by == "customer"]
    if customer_negotiations:
        is_final_round = True  # 有顧客反議價，則這是最終議價階段
    
    # 獲取所有未回應的廚師議價，按時間排序（最新的在前）
    chef_negotiations = [n for n in order.negotiations if n.proposed_by == "chef" and n.is_accepted is None]
    chef_negotiations.sort(key=lambda x: x.created_at, reverse=True)
    
    if chef_negotiations:
        # 取最新的廚師議價
        chef_final_pricing = chef_negotiations[0]
        chef_final_pricing_pending = True
    
    return templates.TemplateResponse("order_detail.html", {
        **commons, 
        "request": request, 
        "user": current_user,
        "order": order,
        "chef_final_pricing_pending": chef_final_pricing_pending,
        "chef_final_pricing": chef_final_pricing,
        "is_final_round": is_final_round
    })

# 新增訂單 - 第零步：選擇廚師
@router.get("/orders/new/step0", name="order_step0")
def get_step0(request: Request, commons=Depends(common_template_params), current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    from models.chef import ChefProfile, ChefSpecialty
    
    # 獲取所有可用的廚師（role為chef的用戶）
    chefs = db.query(User).outerjoin(ChefProfile, User.id == ChefProfile.user_id).filter(
        User.role == "chef"
    ).options(joinedload(User.chef_profile)).all()
    
    # 為每個廚師添加頭像URL和專長顯示
    for chef in chefs:
        if hasattr(chef, 'chef_profile') and chef.chef_profile:
            # 獲取專長列表
            specialties = db.query(ChefSpecialty).filter(ChefSpecialty.chef_id == chef.chef_profile.id).all()
            if specialties:
                chef.chef_profile.specialties_display = ', '.join([s.specialty for s in specialties])
            else:
                chef.chef_profile.specialties_display = '一般料理'
            
            # 使用數據庫中的真實評價數據
            # chef.chef_profile.average_rating 和 total_reviews 已在數據庫中
            pass
        else:
            # 為沒有chef_profile的廚師創建一個臨時profile對象
            class TempProfile:
                def __init__(self):
                    self.kitchen_address = '未設定'
                    self.specialties_display = '一般料理'
                    self.average_rating = None
                    self.total_reviews = 0
                    self.experience_years = None
            
            chef.chef_profile = TempProfile()
    
    return templates.TemplateResponse("add_order_step0.html", {
        **commons, 
        "request": request, 
        "user": current_user,
        "chefs": chefs
    })

# 重新選擇廚師
@router.get("/order/{order_id}/reselect_chef", name="reselect_chef")
def reselect_chef(
    order_id: int,
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    from sqlalchemy.orm import joinedload
    from models.chef import ChefProfile, ChefSpecialty
    
    # 獲取訂單
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # 檢查訂單狀態
    if order.status != OrderStatus.RESELECTING_CHEF:
        raise HTTPException(status_code=400, detail="此訂單不需要重新選擇廚師")
    
    # 獲取所有可用的廚師（排除之前拒絕的廚師）
    chefs = db.query(User).outerjoin(ChefProfile, User.id == ChefProfile.user_id).filter(
        User.role == "chef"
    ).options(joinedload(User.chef_profile)).all()
    
    # 為每個廚師添加頭像URL和專長顯示
    for chef in chefs:
        if hasattr(chef, 'chef_profile') and chef.chef_profile:
            # 獲取專長列表
            specialties = db.query(ChefSpecialty).filter(ChefSpecialty.chef_id == chef.chef_profile.id).all()
            if specialties:
                chef.chef_profile.specialties_display = ', '.join([s.specialty for s in specialties])
            else:
                chef.chef_profile.specialties_display = '一般料理'
        else:
            # 為沒有chef_profile的廚師創建一個臨時profile對象
            class TempProfile:
                def __init__(self):
                    self.kitchen_address = '未設定'
                    self.specialties_display = '一般料理'
                    self.average_rating = None
                    self.total_reviews = 0
                    self.experience_years = None
            
            chef.chef_profile = TempProfile()
    
    # 檢查訂單狀態歷史來判斷原因
    latest_history = db.query(OrderStatusHistory).filter(
        OrderStatusHistory.order_id == order.id,
        OrderStatusHistory.new_status == OrderStatus.RESELECTING_CHEF
    ).order_by(OrderStatusHistory.created_at.desc()).first()
    
    # 根據歷史記錄判斷原因
    reason = "其他原因"
    if latest_history and latest_history.notes:
        if "拒絕接單" in latest_history.notes:
            reason = "廚師拒絕接單"
        elif "議價失敗" in latest_history.notes or "拒絕最終定價" in latest_history.notes or "議價次數用盡" in latest_history.notes:
            reason = "議價失敗"
        elif "拒絕顧客再議價" in latest_history.notes:
            reason = "議價失敗"
    
    return templates.TemplateResponse("reselect_chef.html", {
        **commons,
        "request": request,
        "user": current_user,
        "order": order,
        "chefs": chefs,
        "reason": reason
    })

@router.post("/order/{order_id}/reselect_chef")
def post_reselect_chef(
    order_id: int,
    chef_id: int = Form(...),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.RESELECTING_CHEF:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單不需要重新選擇廚師"}
        )
    
    # 檢查廚師是否存在
    chef = db.query(User).filter(
        User.id == chef_id,
        User.role == "chef"
    ).first()
    
    if not chef:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "廚師不存在"}
        )
    
    try:
        # 更新訂單
        old_status = order.status
        order.chef_id = chef_id
        order.status = OrderStatus.PENDING
        order.negotiation_count = 0  # 重置議價次數
        
        # 記錄狀態歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.PENDING,
            notes=f"顧客重新選擇廚師：{chef.name} ({chef.email})"
        )
        db.add(status_history)
        
        db.commit()
        
        return JSONResponse(
            content={
                "success": True,
                "message": "重新選擇廚師成功！",
                "redirect_url": f"/customer/order/{order_id}"
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"重新選擇廚師失敗：{str(e)}"}
        )

@router.post("/orders/new/step0")
def post_step0(
    request: Request,
    chef_id: int = Form(...),
    db: Session = Depends(get_db)
):
    # 驗證廚師是否存在
    chef = db.query(User).filter(User.id == chef_id, User.role == "chef").first()
    if not chef:
        raise HTTPException(status_code=400, detail="所選廚師不存在")

    # 將選擇的廚師ID保存到session
    request.session["step0"] = {
        "chef_id": chef_id,
        "chef_name": chef.name
    }
    
    return RedirectResponse(url="/customer/orders/new/step1", status_code=status.HTTP_302_FOUND)

# 新增訂單 - 第一步：基本資訊
@router.get("/orders/new/step1", name="order_step1")
def get_step1(request: Request, commons=Depends(common_template_params), current_user: User = Depends(require_customer)):
    # 檢查是否已選擇廚師
    if "step0" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("add_order_step1.html", {**commons, "request": request, "user": current_user})

@router.post("/orders/new/step1")
def post_step1(
    request: Request,
    order_date: str = Form(...),
    order_time: str = Form(...),
    pickup_method: str = Form(...),
    address: str = Form(""),
    customer_notes: str = Form("")
):
    # 檢查是否已選擇廚師
    if "step0" not in request.session:
        raise HTTPException(status_code=400, detail="請先選擇廚師")
    
    # 驗證配送方式
    delivery_method = "delivery" if pickup_method == "外送" else "pickup"
    
    try:
        delivery_method_enum = DeliveryMethod(delivery_method)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的配送方式")
    
    # 如果是外送，地址必填
    if delivery_method_enum == DeliveryMethod.DELIVERY and not address:
        raise HTTPException(status_code=400, detail="外送地址不能為空")
    
    # 解析日期和時間
    try:
        order_datetime = datetime.fromisoformat(f"{order_date}T{order_time}")
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的日期或時間格式")
    
    request.session["step1"] = {
        "order_date": order_date,
        "order_time": order_time,
        "pickup_method": pickup_method,
        "delivery_method": delivery_method,
        "address": address,
        "customer_notes": customer_notes,
        "preferred_time": order_datetime.isoformat()
    }
    
    return RedirectResponse(url="/customer/orders/new/step2?new=true", status_code=status.HTTP_302_FOUND)

# 新增訂單 - 第二步：菜品資訊
@router.get("/orders/new/step2", name="order_step2")
def get_step2(request: Request, commons=Depends(common_template_params), current_user: User = Depends(require_customer)):
    if "step0" not in request.session or "step1" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("add_order_step2.html", {**commons, "request": request, "user": current_user})

@router.post("/orders/new/step2")
def post_step2(
    request: Request,
    dish_names: List[str] = Form(...),
    quantities: List[int] = Form(...),
    salt_levels: List[str] = Form(...),
    spice_levels: List[str] = Form(...),
    include_onions: List[bool] = Form([]),
    include_gingers: List[bool] = Form([]),
    include_garlics: List[bool] = Form([]),
    include_cilantros: List[bool] = Form([]),
    ingredients_list: List[str] = Form([]),
    special_instructions_list: List[str] = Form([]),
    custom_notes_list: List[str] = Form([])
):
    if "step0" not in request.session or "step1" not in request.session:
        raise HTTPException(status_code=400, detail="請先選擇廚師並完成第1步")
    
    dishes = []
    for i in range(len(dish_names)):
        # 驗證枚舉值
        try:
            salt_level = SaltLevel(salt_levels[i])
            spice_level = SpiceLevel(spice_levels[i])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的口味設定 - 菜品{i+1}")
        
        dishes.append({
            "dish_name": dish_names[i],
            "quantity": quantities[i],
            "unit_price": 0,  # 設置默認價格為0，由廚師後續定價
            "dish_price": 0,  # 保持兼容性
            "salt_level": salt_levels[i],
            "spice_level": spice_levels[i],
            "include_onion": i < len(include_onions) and include_onions[i],
            "include_ginger": i < len(include_gingers) and include_gingers[i],
            "include_garlic": i < len(include_garlics) and include_garlics[i],
            "include_cilantro": i < len(include_cilantros) and include_cilantros[i],
            "ingredients": ingredients_list[i] if i < len(ingredients_list) else "",
            "special_instructions": special_instructions_list[i] if i < len(special_instructions_list) else "",
            "custom_notes": custom_notes_list[i] if i < len(custom_notes_list) else ""
        })
    
    request.session["step2"] = {"dishes": dishes}
    return RedirectResponse(url="/customer/orders/new/step3", status_code=status.HTTP_302_FOUND)

# 新增訂單 - 第三步：確認資訊
@router.get("/orders/new/step3", name="order_step3")
def get_step3(request: Request, commons=Depends(common_template_params), current_user: User = Depends(require_customer)):
    if "step0" not in request.session or "step1" not in request.session or "step2" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)

    step0 = request.session["step0"]
    step1 = request.session["step1"]
    dishes = request.session["step2"]["dishes"]
    
    return templates.TemplateResponse(
        "add_order_step3.html",
        {
            **commons,
            "request": request,
            "user": current_user,
            "step0": step0,
            "step1": step1,
            "dishes": dishes
        }
    )

@router.post("/orders/new/step3")
def post_step3(request: Request):
    if "step0" not in request.session or "step1" not in request.session or "step2" not in request.session:
        raise HTTPException(status_code=400, detail="資料不完整")
    
    return RedirectResponse(url="/customer/orders/new/step4", status_code=status.HTTP_302_FOUND)

# 新增訂單 - 第四步：最终确认和提交
@router.get("/orders/new/step4", name="order_step4")
def get_step4(request: Request, commons=Depends(common_template_params), current_user: User = Depends(require_customer)):
    if "step0" not in request.session or "step1" not in request.session or "step2" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)

    step0 = request.session["step0"]
    step1 = request.session["step1"]
    dishes = request.session["step2"]["dishes"]

    return templates.TemplateResponse(
        "add_order_step4.html",
        {
            **commons,
            "request": request,
            "user": current_user,
            "step0": step0,
            "step1": step1,
            "dishes": dishes
        }
    )

@router.post("/orders/new/step4")
def post_step4(
    request: Request,
    contact_phone: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    if "step0" not in request.session or "step1" not in request.session or "step2" not in request.session:
        raise HTTPException(status_code=400, detail="資料不完整")

    step0 = request.session["step0"]
    step1 = request.session["step1"]
    dishes = request.session["step2"]["dishes"]
    
    try:
        # 計算總金額 - 設為0，由廚師後續定價
        total_amount = 0  
        delivery_fee = 50.0 if step1["delivery_method"] == "delivery" else 0.0
        
        # 創建訂單
        order = Order(
            customer_id=current_user.id,
            chef_id=step0["chef_id"],  # 添加廚師ID
            order_number=f"ORD{uuid.uuid4().hex[:8].upper()}",
            status=OrderStatus.PENDING,
            delivery_method=DeliveryMethod(step1["delivery_method"]),
            delivery_address=step1.get("address"),
            delivery_notes="",  # 可以後續添加
            preferred_time=datetime.fromisoformat(step1["preferred_time"]) if step1.get("preferred_time") else None,
            total_amount=total_amount,
            delivery_fee=delivery_fee,
            customer_notes=step1.get("customer_notes")
    )
        
        db.add(order)
        db.commit()
        db.refresh(order)

        # 創建訂單菜品
        for dish_data in dishes:
            order_dish = OrderDish(
                order_id=order.id,
                dish_name=dish_data["dish_name"],
                quantity=dish_data["quantity"],
                unit_price=0,  # 設為0，由廚師後續定價
                salt_level=SaltLevel(dish_data["salt_level"]),
                spice_level=SpiceLevel(dish_data["spice_level"]),
                include_onion=dish_data.get("include_onion", True),
                include_ginger=dish_data.get("include_ginger", True),
                include_garlic=dish_data.get("include_garlic", True),
                include_cilantro=dish_data.get("include_cilantro", True),
                ingredients=dish_data.get("ingredients"),
                special_instructions=dish_data.get("special_instructions"),
                custom_notes=dish_data.get("custom_notes")
            )
            db.add(order_dish)
        
        db.commit()

        # 創建通知給廚師：收到新訂單
        create_notification(
            db=db,
            user_id=step0["chef_id"],
            notification_type=NotificationType.NEW_ORDER,
            title="收到新訂單",
            content=f"顧客 {current_user.name} 向您下了新訂單！",
            order_id=order.id
        )
        
        db.commit()

        # 清除 session 數據
        request.session.pop("step0", None)
        request.session.pop("step1", None)
        request.session.pop("step2", None)

        return RedirectResponse(
            url=f"/customer/order/{order.id}?success=1", 
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"創建訂單失敗：{str(e)}")

# 更新顧客個人資料
@router.post("/profile/update")
async def update_customer_profile(
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    try:
        # 更新基本資料
        current_user.name = name
        if phone:
            current_user.phone = phone
        
        # 處理密碼更新
        if new_password:
            # OAuth2用戶不能修改密碼
            if current_user.oauth_provider:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "OAuth2登入用戶無法修改密碼，請前往您的Google帳戶設定"}
                )
            
            if not current_password:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "請輸入目前密碼"}
                )
            
            # 驗證目前密碼
            if not current_user.hashed_password or not verify_password(current_password, current_user.hashed_password):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "目前密碼錯誤"}
                )
            
            # 設置新密碼
            current_user.hashed_password = get_password_hash(new_password)
        
        # 處理頭像上傳
        if avatar and avatar.filename:
            # 確保uploads目錄存在
            os.makedirs("static/uploads/avatars", exist_ok=True)
            
            # 生成唯一檔名
            file_extension = avatar.filename.split('.')[-1] if '.' in avatar.filename else 'jpg'
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"static/uploads/avatars/{filename}"
            
            # 儲存檔案
            with open(file_path, "wb") as buffer:
                content = await avatar.read()
                buffer.write(content)
            
            current_user.avatar_url = f"/static/uploads/avatars/{filename}"
        
        # 更新時間戳
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        # 準備響應並更新cookies
        response = JSONResponse(content={"success": True, "message": "個人資料更新成功！"})
        
        # 更新頭像cookie（如果有新頭像）
        if avatar and avatar.filename and current_user.avatar_url:
            response.set_cookie(key="avatar_url", value=current_user.avatar_url, httponly=False)
        
        return response
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"更新失敗：{str(e)}"}
        )

# 顧客回應議價
@router.post("/order/{order_id}/respond_negotiation/{negotiation_id}")
def respond_negotiation(
    order_id: int,
    negotiation_id: int,
    response_data: NegotiationResponse,
    current_user: User = Depends(require_customer),
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
    if order.customer_id != current_user.id:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "無權操作此訂單"}
        )
    
    # 獲取議價記錄
    negotiation = db.query(Negotiation).filter(
        Negotiation.id == negotiation_id,
        Negotiation.order_id == order_id
    ).first()
    
    if not negotiation:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "議價記錄不存在"}
        )
    
    # 檢查是否已回應
    if negotiation.is_accepted is not None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此議價已回應過"}
        )
    
    try:
        # 更新議價記錄
        negotiation.is_accepted = response_data.is_accepted
        negotiation.response_message = response_data.response_message
        negotiation.responded_at = datetime.utcnow()
        
        if response_data.is_accepted:
            # 顧客接受議價，訂單狀態改為已接單
            order.status = OrderStatus.ACCEPTED
            order.total_amount = negotiation.proposed_amount
            
            # 記錄狀態歷史
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=OrderStatus.NEGOTIATING,
                new_status=OrderStatus.ACCEPTED,
                notes=f"顧客接受議價：NT${negotiation.proposed_amount}"
            )
            db.add(status_history)
            
            message = "議價已接受，訂單確認成功！"
            
        else:
            # 顧客拒絕議價
            action = "拒絕"
            
            # 如果顧客提供了再議價金額，創建新的議價記錄
            if response_data.counter_amount and response_data.counter_amount > 0:
                order.negotiation_count += 1
                
                # 創建顧客的再議價記錄
                counter_negotiation = Negotiation(
                    order_id=order.id,
                    proposed_amount=response_data.counter_amount,
                    proposed_by="customer",
                    message=response_data.response_message,
                    created_at=datetime.utcnow()
                )
                db.add(counter_negotiation)
                
                status_history = OrderStatusHistory(
                    order_id=order.id,
                    old_status=OrderStatus.NEGOTIATING,
                    new_status=OrderStatus.NEGOTIATING,
                    notes=f"顧客拒絕議價並提出再議價：NT${response_data.counter_amount}"
                )
                message = "已提交再議價，等待廚師回應"
                
            else:
                # 單純拒絕，檢查議價次數
                if order.negotiation_count >= 2:
                    order.status = OrderStatus.RESELECTING_CHEF
                    order.chef_id = None  # 清除廚師分配，讓顧客重新選擇
                    status_history = OrderStatusHistory(
                        order_id=order.id,
                        old_status=OrderStatus.NEGOTIATING,
                        new_status=OrderStatus.RESELECTING_CHEF,
                        notes="議價次數用盡，顧客可重新選擇廚師"
                    )
                    message = "議價已拒絕，您可以重新選擇廚師"
                else:
                    status_history = OrderStatusHistory(
                        order_id=order.id,
                        old_status=OrderStatus.NEGOTIATING,
                        new_status=OrderStatus.NEGOTIATING,
                        notes=f"顧客拒絕議價：NT${negotiation.proposed_amount}"
                    )
                    message = "議價已拒絕，可等待廚師再次議價"
            
            db.add(status_history)
        
        # 創建通知給廚師：顧客回應議價
        if response_data.is_accepted:
            create_notification(
                db=db,
                user_id=order.chef_id,
                notification_type=NotificationType.NEGOTIATION_RESPONSE,
                title="顧客接受了您的議價",
                content=f"顧客 {current_user.name} 接受了您的議價 NT${negotiation.proposed_amount}！",
                order_id=order.id
            )
        else:
            # 如果有再議價
            if response_data.counter_amount and response_data.counter_amount > 0:
                create_notification(
                    db=db,
                    user_id=order.chef_id,
                    notification_type=NotificationType.NEGOTIATION_RESPONSE,
                    title="顧客提出再議價",
                    content=f"顧客 {current_user.name} 提出再議價 NT${response_data.counter_amount}！",
                    order_id=order.id
                )
            else:
                create_notification(
                    db=db,
                    user_id=order.chef_id,
                    notification_type=NotificationType.NEGOTIATION_RESPONSE,
                    title="顧客拒絕了您的議價",
                    content=f"顧客 {current_user.name} 拒絕了您的議價。",
                    order_id=order.id
                )
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": message}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"回應失敗：{str(e)}"}
        )

# 顧客查看最終定價
@router.get("/order/{order_id}/final_pricing", name="customer_final_pricing")
def customer_final_pricing(
    order_id: int,
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    from sqlalchemy.orm import joinedload
    
    # 獲取訂單
    order = db.query(Order).options(
        joinedload(Order.dishes),
        joinedload(Order.negotiations)
    ).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # 檢查是否有廚師的最終定價
    chef_final_pricing = None
    for nego in order.negotiations:
        if nego.proposed_by == "chef" and nego.is_accepted is None:
            chef_final_pricing = nego
            break
    
    if not chef_final_pricing:
        raise HTTPException(status_code=400, detail="沒有找到廚師的最終定價")
    
    # 計算顧客已經議價的次數（用於判斷是否為第一次報價）
    customer_counter_count = sum(
        1 for nego in order.negotiations 
        if nego.proposed_by == "customer"
    )
    
    # is_first_pricing: True表示這是廚師第一次報價，顧客還沒反議價過
    is_first_pricing = (customer_counter_count == 0)
    
    return templates.TemplateResponse(
        "customer_final_pricing.html",
        {
            **commons,
            "request": request,
            "user": current_user,
            "order": order,
            "chef_final_pricing": chef_final_pricing,
            "is_first_pricing": is_first_pricing
        }
    )

# 顧客回應最終定價
@router.post("/order/{order_id}/respond_final_pricing/{negotiation_id}")
def respond_final_pricing(
    order_id: int,
    negotiation_id: int,
    response_data: dict,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 獲取廚師的最終定價記錄
    negotiation = db.query(Negotiation).filter(
        Negotiation.id == negotiation_id,
        Negotiation.order_id == order_id,
        Negotiation.proposed_by == "chef"
    ).first()
    
    if not negotiation:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "議價記錄不存在"}
        )
    
    # 檢查是否已經回應過
    if negotiation.is_accepted is not None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此議價已回應過"}
        )
    
    try:
        is_accepted = response_data.get('is_accepted', False)
        
        # 更新議價記錄
        negotiation.is_accepted = is_accepted
        negotiation.responded_at = datetime.utcnow()
        
        if is_accepted:
            # 顧客接受最終定價 → 訂單狀態變成已接單
            order.status = OrderStatus.ACCEPTED
            order.total_amount = negotiation.proposed_amount
            
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=OrderStatus.NEGOTIATING,
                new_status=OrderStatus.ACCEPTED,
                notes=f"顧客接受最終定價：NT${negotiation.proposed_amount}"
            )
            message = "已接受最終定價，訂單確認成功！"
            
        else:
            # 顧客拒絕最終定價 → 重新選擇廚師
            # 先保存廚師ID，用於創建通知
            chef_id_for_notification = order.chef_id
            order.status = OrderStatus.RESELECTING_CHEF
            order.chef_id = None  # 清除廚師分配，讓顧客重新選擇
            
            status_history = OrderStatusHistory(
                order_id=order.id,
                old_status=OrderStatus.NEGOTIATING,
                new_status=OrderStatus.RESELECTING_CHEF,
                notes=f"顧客拒絕最終定價，可重新選擇廚師"
            )
            message = "已拒絕最終定價，您可以重新選擇廚師"
        
        db.add(status_history)
        
        # 創建通知給廚師：顧客回應議價
        if is_accepted:
            create_notification(
                db=db,
                user_id=order.chef_id,
                notification_type=NotificationType.NEGOTIATION_RESPONSE,
                title="顧客接受了最終定價",
                content=f"顧客 {current_user.name} 接受了您的最終定價 NT${negotiation.proposed_amount}！",
                order_id=order.id
            )
        else:
            create_notification(
                db=db,
                user_id=chef_id_for_notification,
                notification_type=NotificationType.NEGOTIATION_RESPONSE,
                title="顧客拒絕了最終定價",
                content=f"顧客 {current_user.name} 拒絕了您的最終定價，訂單已取消。",
                order_id=order.id
            )
        
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

# 提交評分
@router.post("/order/{order_id}/review")
def submit_review(
    order_id: int,
    review_data: ReviewRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查訂單狀態
    if order.status != OrderStatus.COMPLETED:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "只有已完成的訂單才能評價"}
        )
    
    # 檢查是否已經評價過
    existing_review = db.query(Review).filter(Review.order_id == order_id).first()
    if existing_review:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "此訂單已經評價過"}
        )
    
    # 驗證評分
    if review_data.rating < 1 or review_data.rating > 5:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "評分必須在1-5之間"}
        )
    
    try:
        # 創建評價記錄
        review = Review(
            order_id=order.id,
            reviewer_id=current_user.id,
            reviewee_id=order.chef_id,
            rating=review_data.rating,
            content=review_data.content or "",
            created_at=datetime.utcnow()
        )
        db.add(review)
        
        # 更新廚師的平均評分
        if order.chef and order.chef.chef_profile:
            # 計算該廚師的平均評分
            chef_reviews = db.query(Review).filter(Review.reviewee_id == order.chef_id).all()
            if chef_reviews:
                total_rating = sum(r.rating for r in chef_reviews) + review_data.rating
                total_reviews = len(chef_reviews) + 1
                avg_rating = total_rating / total_reviews
                
                # 更新廚師資料
                order.chef.chef_profile.average_rating = round(avg_rating, 1)
                order.chef.chef_profile.total_reviews = total_reviews
        
        # 創建通知給廚師：收到新評價
        create_notification(
            db=db,
            user_id=order.chef_id,
            notification_type=NotificationType.NEW_REVIEW,
            title=f"#{order.id} 收到了評價",
            content=f"顧客對訂單#{order.id} 給了 {review_data.rating} 星評價！",
            order_id=order.id,
            review_id=review.id
        )
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "評價提交成功！"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"評價提交失敗：{str(e)}"}
        )

@router.post("/order/{order_id}/confirm_received")
def confirm_received(
    order_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # 獲取訂單
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "訂單不存在"}
        )
    
    # 檢查訂單狀態，只有製作完成狀態才能確認收貨
    if order.status != OrderStatus.READY:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "只有製作完成的訂單才能確認收貨"}
        )
    
    try:
        # 更新訂單狀態為交付完成
        old_status = order.status
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        
        # 記錄狀態變更歷史
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.COMPLETED,
            notes="顧客確認收貨，訂單完成"
        )
        db.add(status_history)
        
        # 創建通知給廚師：顧客確認收貨
        create_notification(
            db=db,
            user_id=order.chef_id,
            notification_type=NotificationType.ORDER_COMPLETED,
            title="訂單已完成",
            content=f"顧客已確認收貨，訂單#{order.id} 完成！",
            order_id=order.id
        )
        
        db.commit()
        
        return JSONResponse(
            content={"success": True, "message": "訂單已完成！"}
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"操作失敗：{str(e)}"}
        )


# 身心障礙者/高齡者驗證申請頁面
@router.get("/special-needs-verification")
def special_needs_verification_page(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse("special_needs_verification.html", {
        **commons,
        "request": request,
        "user": current_user
    })


# 提交身心障礙者/高齡者驗證申請
@router.post("/special-needs-verification")
async def submit_special_needs_verification(
    request: Request,
    special_needs_type: str = Form(...),
    document_image: UploadFile = File(...),
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    try:
        # 檢查是否已經有申請記錄
        if current_user.special_needs_type:
            return templates.TemplateResponse("special_needs_verification.html", {
                **commons,
                "request": request,
                "user": current_user,
                "error": "您已經提交過申請，請勿重複申請"
            })
        
        # 驗證申請類型
        if special_needs_type not in ['disability', 'elderly']:
            return templates.TemplateResponse("special_needs_verification.html", {
                **commons,
                "request": request,
                "user": current_user,
                "error": "無效的申請類型"
            })
        
        # 驗證檔案類型
        if not document_image.content_type.startswith('image/'):
            return templates.TemplateResponse("special_needs_verification.html", {
                **commons,
                "request": request,
                "user": current_user,
                "error": "請上傳圖片檔案（JPG、PNG 格式）"
            })
        
        # 檢查檔案大小 (10MB)
        content = await document_image.read()
        if len(content) > 10 * 1024 * 1024:
            return templates.TemplateResponse("special_needs_verification.html", {
                **commons,
                "request": request,
                "user": current_user,
                "error": "檔案大小不能超過 10MB"
            })
        
        # 創建上傳目錄
        upload_dir = "static/uploads/special_needs"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一檔名
        file_extension = document_image.filename.split('.')[-1] if '.' in document_image.filename else 'jpg'
        filename = f"special_needs_{current_user.id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # 保存檔案
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 更新用戶資料
        current_user.special_needs_type = special_needs_type
        current_user.special_needs_document_url = f"/static/uploads/special_needs/{filename}"
        current_user.special_needs_verified = False  # 待審核
        current_user.special_needs_applied_at = datetime.utcnow()
        
        db.commit()
        
        return templates.TemplateResponse("special_needs_verification.html", {
            **commons,
            "request": request,
            "user": current_user,
            "success": "申請已成功提交！"
        })
        
    except Exception as e:
        # 如果保存失敗，刪除檔案
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        db.rollback()
        
        return templates.TemplateResponse("special_needs_verification.html", {
            **commons,
            "request": request,
            "user": current_user,
            "error": f"申請提交失敗：{str(e)}"
        })


# 查看身心障礙者/高齡者驗證狀態
@router.get("/special-needs-status")
def special_needs_status_page(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # 計算預計完成時間（申請後3個工作天）
    estimated_completion = None
    if current_user.special_needs_applied_at:
        estimated_completion = current_user.special_needs_applied_at + timedelta(days=3)
    
        return templates.TemplateResponse("special_needs_status.html", {
            **commons,
            "request": request,
            "user": current_user,
            "estimated_completion": estimated_completion
        })


# 語音AI助手訂單頁面
@router.get("/orders/new/voice_assistant", name="voice_order_assistant")
def voice_order_assistant_page(
    request: Request,
    chef_id: int,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """語音AI助手訂單頁面"""
    # 驗證廚師是否存在
    chef = db.query(User).filter(
        User.id == chef_id,
        User.role == "chef"
    ).first()
    
    if not chef:
        raise HTTPException(status_code=404, detail="廚師不存在")
    
    return templates.TemplateResponse("voice_order_assistant.html", {
        **commons,
        "request": request,
        "user": current_user,
        "chef": chef
    })


# 處理語音AI助手的訊息
@router.post("/orders/new/voice_assistant/process")
async def process_voice_message(
    request_data: VoiceOrderRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """處理語音AI助手的訊息並返回AI回應"""
    try:
        import json
        from config import get_settings
        settings = get_settings()
        
        # 設置OpenAI API
        openai.api_key = settings.OPENAI_API_KEY
        
        # 獲取當前訂單資料
        order_data = request_data.order_data
        chef_name = order_data.get('chef_name', '')
        order_date = order_data.get('order_date', '')
        order_time = order_data.get('order_time', '')
        delivery_method = order_data.get('delivery_method', '')
        delivery_address = order_data.get('delivery_address', '')
        dishes = order_data.get('dishes', [])
        customer_notes = order_data.get('customer_notes', '')
        
        # 獲取當前日期時間
        from datetime import datetime
        today = datetime.now()
        current_year = today.year
        current_date = today.strftime('%Y-%m-%d')
        current_time = today.strftime('%H:%M')
        
        # 構建系統提示 - 結構化引導
        system_prompt = f"""你是一個專業且友善的訂餐助手，負責引導顧客完成訂單。

【當前系統時間】
今天日期：{current_date}
當前時間：{current_time}
年份：{current_year}

【當前訂單狀態】
廚師：{chef_name if chef_name else '未設定'}
日期：{order_date if order_date else '未設定'}
時間：{order_time if order_time else '未設定'}
取餐方式：{delivery_method if delivery_method else '未設定'}
地址：{delivery_address if delivery_address else '未設定'}
菜色：{json.dumps(dishes, ensure_ascii=False) if dishes else '尚無菜色'}
備註：{customer_notes if customer_notes else '無'}

【收集流程】
請按照以下順序引導顧客：
1. 如果沒有日期和時間 → 詢問「請問您想在什麼時候用餐？」
2. 如果沒有取餐方式 → 詢問「請問您要外送還是自取？」
3. 如果選外送但沒地址 → 詢問「請提供外送地址」
4. 如果沒有菜色 → 詢問「請告訴我您想吃什麼菜？」
5. 對於每道菜，詢問：
   - 菜名和數量
   - 鹹度偏好（清淡/正常/重鹹）
   - 辣度偏好（不辣/微辣/中辣/辣/超辣）
   - 是否需要蔥、薑、蒜、香菜
   - 特殊要求

【日期時間處理規則】
1. 如果顧客只說「10月15日」或「10/15」，自動補上當前年份 {current_year}
2. 如果顧客說「今天」，使用 {current_date}
3. 如果顧客說「明天」，使用明天的日期
4. 如果顧客說「後天」，使用後天的日期
5. 如果顧客說「週X」或「星期X」，計算對應的日期
6. 時間格式統一為 24 小時制 HH:MM
7. 如果顧客說「中午」，使用 12:00
8. 如果顧客說「晚上7點」，使用 19:00
9. 所有日期必須是 YYYY-MM-DD 格式

【語音辨識錯別字修正】
顧客可能使用語音輸入，請智能修正常見錯別字：
- 「水煮魚」可能被辨識為「水著魚」「水主魚」
- 「宮保雞丁」可能被辨識為「公保雞丁」「工保雞丁」「公寶基頂」「宮寶雞丁」
- 「麻婆豆腐」可能被辨識為「馬婆豆腐」「麻波豆腐」
- 「糖醋排骨」可能被辨識為「糖促排骨」「湯醋排骨」
- 「清蒸魚」可能被辨識為「清爭魚」「清蒸魯魚」「清正魚」
- 「外送」可能被辨識為「外宋」「外送」
- 「自取」可能被辨識為「自曲」「資取」「自取」
- 數字可能被辨識為中文（一、二、三、兩）或阿拉伯數字（1、2、3）
- 「兩份」「2份」「二份」都表示數量2
- 根據上下文智能判斷並修正為正確的菜名和數量

【回應格式】
你必須以JSON格式回應，包含：
{{
  "response": "給顧客的友善回應（繁體中文）",
  "order_data": {{
    "order_date": "{order_date if order_date else 'null'}",
    "order_time": "{order_time if order_time else 'null'}",
    "delivery_method": "{delivery_method if delivery_method else 'null'}",
    "delivery_address": "{delivery_address if delivery_address else 'null'}",
    "dishes": {json.dumps(dishes, ensure_ascii=False) if dishes else '[]'},
    "customer_notes": "{customer_notes if customer_notes else 'null'}"
  }},
  "is_complete": false或true
}}

**重要**：以上 order_data 是當前已有的資料，你必須：
1. 保留所有已有的值（如上所示）
2. 只更新顧客這次提到的欄位
3. 如果顧客沒提到某個欄位，保持原值
4. 例如：如果已有日期和取餐方式，顧客只回答菜色口味，則保留日期和取餐方式，只更新菜色資訊
5. **菜色的 quantity 必須是數字（1, 2, 3），不能是字串或undefined**
6. 菜色範例：{{"dish_name": "宮保雞丁", "quantity": 2, "salt_level": "normal", "spice_level": "mild", "include_onion": true, "include_ginger": true, "include_garlic": true, "include_cilantro": true}}

【重要規則】
1. 一次只問一個問題，不要一次問太多
2. 用友善、口語化的方式回應
3. 自動修正語音辨識的錯別字
4. 日期必須包含完整年份（YYYY-MM-DD）
5. 如果顧客沒提到年份，自動使用 {current_year} 年
6. 只有當所有必要資訊都收集完成時，才設定 is_complete 為 true
7. 必要資訊：日期、時間、取餐方式、至少一道菜（含菜名、數量、鹹度、辣度）
8. 如果是外送，地址也是必要的
9. 回應必須是有效的JSON格式
10. 確認日期不早於今天 {current_date}

【資料保留規則 - 非常重要！】
1. **必須保留所有已收集的資訊**：如果當前訂單狀態中已有資料，除非顧客明確要修改，否則必須保留
2. 在 order_data 中，只更新顧客這次提到的欄位，其他欄位保持原值
3. 如果顧客說「都可以」「隨便」「沒關係」等，表示接受預設值，但**不要清空已有資料**
4. 對於「都可以」的回應：
   - 鹹度設為 "normal"
   - 辣度設為 "none"
   - 蔥薑蒜香菜都設為 true
   - **保留已有的菜色、日期、時間、取餐方式等資訊**
5. 範例：如果已有日期和菜色，顧客回答口味偏好時，只更新菜色的口味設定，不要清空日期"""
        
        # 構建用戶訊息，包含上下文提示
        user_message = f"""顧客說：「{request_data.message}」

請記住：
1. 保留所有已收集的訂單資訊（日期、時間、取餐方式、菜色等）
2. 只更新顧客這次提到的內容
3. 如果顧客說「都可以」「隨便」，使用預設值但保留其他已有資訊
4. 在 order_data 中，沒有提到的欄位請保持原值（從當前訂單狀態複製）"""
        
        # 調用OpenAI API (使用新版API)
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # 解析JSON回應
        try:
            # 移除可能的markdown代碼塊標記
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.startswith('```'):
                ai_response = ai_response[3:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()
            
            parsed_response = json.loads(ai_response)
            response_text = parsed_response.get('response', '抱歉，我無法理解您的訊息。')
            updated_order_data = parsed_response.get('order_data', {})
            is_complete = parsed_response.get('is_complete', False)
            
            return JSONResponse(content={
                "success": True,
                "response": response_text,
                "order_data": updated_order_data,
                "is_complete": is_complete
            })
            
        except json.JSONDecodeError as e:
            # JSON解析失敗，返回原始回應
            return JSONResponse(content={
                "success": True,
                "response": ai_response,
                "order_data": {},
                "is_complete": False
            })
        
    except Exception as e:
        import traceback
        print(f"Error in process_voice_message: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"處理訊息時發生錯誤：{str(e)}"
            }
        )


# 語音轉文字
@router.post("/orders/new/voice_assistant/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(require_customer)
):
    """將語音轉換為文字"""
    temp_file_path = None
    try:
        # 檢查文件大小
        content = await audio.read()
        if len(content) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "音訊檔案為空，請重新錄製"
                }
            )
        
        # 創建臨時文件（使用原始格式）
        file_extension = audio.filename.split('.')[-1] if '.' in audio.filename else 'webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 使用Whisper進行語音轉文字
            print(f"Transcribing audio file: {temp_file_path}, size: {len(content)} bytes")
            model = whisper.load_model("base")
            result = model.transcribe(temp_file_path, language="zh", fp16=False)
            
            transcribed_text = result["text"].strip()
            
            if not transcribed_text:
                return JSONResponse(content={
                    "success": False,
                    "message": "無法識別語音內容，請說清楚一點後重試"
                })
            
            print(f"Transcription successful: {transcribed_text}")
            
            return JSONResponse(content={
                "success": True,
                "text": transcribed_text
            })
            
        except Exception as e:
            import traceback
            print(f"Whisper transcription error: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"語音識別失敗：{str(e)}"
                }
            )
            
    except Exception as e:
        import traceback
        print(f"Audio transcription error: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"處理音訊時發生錯誤：{str(e)}"
            }
        )
    finally:
        # 清理臨時文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Failed to delete temp file: {e}")


# 提交語音AI助手創建的訂單
@router.post("/orders/new/voice_assistant/submit")
async def submit_voice_order(
    order_data: VoiceOrderData,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """提交語音AI助手創建的訂單"""
    try:
        # 驗證廚師是否存在
        chef = db.query(User).filter(
            User.id == order_data.chef_id,
            User.role == "chef"
        ).first()
        
        if not chef:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "廚師不存在"}
            )
        
        # 解析日期和時間
        if order_data.order_date and order_data.order_time:
            try:
                order_datetime = datetime.fromisoformat(f"{order_data.order_date}T{order_data.order_time}")
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "無效的日期或時間格式"}
                )
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "缺少日期或時間資訊"}
            )
        
        # 驗證配送方式
        if not order_data.delivery_method:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "缺少取餐方式資訊"}
            )
        
        # 接受中文或英文的配送方式
        delivery_method_str = order_data.delivery_method
        if delivery_method_str in ['外送', 'delivery']:
            delivery_method_enum = DeliveryMethod.DELIVERY
        elif delivery_method_str in ['自取', 'pickup']:
            delivery_method_enum = DeliveryMethod.PICKUP
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"無效的配送方式：{delivery_method_str}"}
            )
        
        # 如果是外送，地址必填
        if delivery_method_enum == DeliveryMethod.DELIVERY and not order_data.delivery_address:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "外送地址不能為空"}
            )
        
        # 驗證菜色
        if not order_data.dishes or len(order_data.dishes) == 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "至少需要一個菜色"}
            )
        
        # 創建訂單
        order = Order(
            customer_id=current_user.id,
            chef_id=order_data.chef_id,
            order_number=f"ORD{uuid.uuid4().hex[:8].upper()}",
            status=OrderStatus.PENDING,
            delivery_method=delivery_method_enum,
            delivery_address=order_data.delivery_address,
            delivery_notes="",
            preferred_time=order_datetime,
            total_amount=0,  # 設為0，由廚師後續定價
            delivery_fee=50.0 if delivery_method_enum == DeliveryMethod.DELIVERY else 0.0,
            customer_notes=order_data.customer_notes
        )
        
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # 創建訂單菜品
        for dish_data in order_data.dishes:
            try:
                salt_level = SaltLevel(dish_data.get("salt_level", "normal"))
                spice_level = SpiceLevel(dish_data.get("spice_level", "none"))
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": f"無效的口味設定 - {dish_data.get('dish_name', '未知菜色')}"}
                )
            
            order_dish = OrderDish(
                order_id=order.id,
                dish_name=dish_data["dish_name"],
                quantity=dish_data.get("quantity", 1),
                unit_price=0,  # 設為0，由廚師後續定價
                salt_level=salt_level,
                spice_level=spice_level,
                include_onion=dish_data.get("include_onion", True),
                include_ginger=dish_data.get("include_ginger", True),
                include_garlic=dish_data.get("include_garlic", True),
                include_cilantro=dish_data.get("include_cilantro", True),
                ingredients=dish_data.get("ingredients", ""),
                special_instructions=dish_data.get("special_instructions", ""),
                custom_notes=dish_data.get("custom_notes", "")
            )
            db.add(order_dish)
        
        db.commit()
        
        # 創建通知給廚師：收到新訂單
        create_notification(
            db=db,
            user_id=order_data.chef_id,
            notification_type=NotificationType.NEW_ORDER,
            title="收到新訂單",
            content=f"顧客 {current_user.name} 向您下了新訂單！",
            order_id=order.id
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "訂單創建成功！",
            "order_id": order.id,
            "order_number": order.order_number
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"創建訂單失敗：{str(e)}"}
        )



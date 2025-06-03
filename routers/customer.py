from fastapi import APIRouter, Request, Form, HTTPException, Depends, status, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import os

from database import get_db
from models.user import User
from models.order import Order, OrderStatus, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel, Negotiation, OrderStatusHistory
from utils.dependencies import require_customer, common_template_params
from utils.security import get_password_hash, verify_password
from pydantic import BaseModel

router = APIRouter(dependencies=[Depends(require_customer)])
templates = Jinja2Templates(directory="templates")

class NegotiationResponse(BaseModel):
    is_accepted: bool
    response_message: Optional[str] = None
    counter_amount: Optional[float] = None

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
        joinedload(Order.dishes)
    ).filter(Order.customer_id == current_user.id).order_by(Order.created_at.desc()).all()
    
    return templates.TemplateResponse("order_list.html", {**commons, "request": request, "orders": orders})

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
    
    return templates.TemplateResponse("order_detail.html", {**commons, "request": request, "order": order})

# 新增訂單 - 第零步：選擇廚師
@router.get("/orders/new/step0", name="order_step0")
def get_step0(request: Request, commons=Depends(common_template_params), db: Session = Depends(get_db)):
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
        "chefs": chefs
    })

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
def get_step1(request: Request, commons=Depends(common_template_params)):
    # 檢查是否已選擇廚師
    if "step0" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("add_order_step1.html", {**commons, "request": request})

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
    
    return RedirectResponse(url="/customer/orders/new/step2", status_code=status.HTTP_302_FOUND)

# 新增訂單 - 第二步：菜品資訊
@router.get("/orders/new/step2", name="order_step2")
def get_step2(request: Request, commons=Depends(common_template_params)):
    if "step0" not in request.session or "step1" not in request.session:
        return RedirectResponse(url="/customer/orders/new/step0", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("add_order_step2.html", {**commons, "request": request})

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
def get_step3(request: Request, commons=Depends(common_template_params)):
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
def get_step4(request: Request, commons=Depends(common_template_params)):
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
            if not current_password:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "請輸入目前密碼"}
                )
            
            # 驗證目前密碼（OAuth用戶可能沒有密碼）
            if current_user.hashed_password and not verify_password(current_password, current_user.hashed_password):
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
        
        return JSONResponse(content={"success": True, "message": "個人資料更新成功！"})
        
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
                    order.status = OrderStatus.CANCELLED
                    status_history = OrderStatusHistory(
                        order_id=order.id,
                        old_status=OrderStatus.NEGOTIATING,
                        new_status=OrderStatus.CANCELLED,
                        notes="議價次數用盡，訂單自動取消"
                    )
                    message = "議價已拒絕，訂單已取消"
                else:
                    status_history = OrderStatusHistory(
                        order_id=order.id,
                        old_status=OrderStatus.NEGOTIATING,
                        new_status=OrderStatus.NEGOTIATING,
                        notes=f"顧客拒絕議價：NT${negotiation.proposed_amount}"
                    )
                    message = "議價已拒絕，可等待廚師再次議價"
            
            db.add(status_history)
        
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



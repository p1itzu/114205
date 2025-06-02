from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import uuid

from database import get_db
from models.user import User
from models.order import Order, OrderStatus, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel
from utils.dependencies import require_customer, common_template_params

router = APIRouter(dependencies=[Depends(require_customer)])
templates = Jinja2Templates(directory="templates")

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
        joinedload(Order.dishes)
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
            
            # 計算平均評價（後續可以實現）
            chef.chef_profile.average_rating = 4.5  # 暫時設定
        else:
            # 為沒有chef_profile的廚師創建一個臨時profile對象
            class TempProfile:
                def __init__(self):
                    self.kitchen_address = '未設定'
                    self.specialties_display = '一般料理'
                    self.average_rating = None
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
    unit_prices: List[float] = Form(...),
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
            "unit_price": unit_prices[i],
            "dish_price": unit_prices[i],  # 保持兼容性
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
    
    # 計算總金額
    total_amount = sum(dish["unit_price"] * dish["quantity"] for dish in dishes)
    delivery_fee = 50.0 if step1["delivery_method"] == "delivery" else 0.0
    
    return templates.TemplateResponse(
        "add_order_step3.html",
        {
            **commons,
            "request": request,
            "step0": step0,
            "step1": step1,
            "dishes": dishes,
            "total_amount": total_amount,
            "delivery_fee": delivery_fee,
            "final_total": total_amount + delivery_fee
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
        # 計算總金額
        total_amount = sum(dish["unit_price"] * dish["quantity"] for dish in dishes)
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
                unit_price=dish_data["unit_price"],
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



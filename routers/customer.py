from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, time

from typing import List
from fastapi import Form
from models.user import User

from database import get_db
from schemas.order import Step1, Step2, Step4, OrderCreate
from models.order import Order as OrderModel, Dish as DishModel, DishIngredient as IngredientModel
from utils.security import decode_access_token
from models.order import Order

from utils.dependencies import require_customer, common_template_params

router = APIRouter(dependencies=[Depends(require_customer)])
templates = Jinja2Templates(directory="templates")

#list orders

@router.get("/orders/list", name="customer_order_list")
def order_list_page(request: Request, commons=Depends(common_template_params),db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return templates.TemplateResponse(
        "order_list.html",
        {**commons, "request": request, "orders": orders}
    )

@router.get("/order/{order_id}", name="order_detail")
def order_detail(order_id: int, request: Request, commons=Depends(common_template_params), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    return templates.TemplateResponse("order_detail.html", {**commons, "request": request, "order": order})

#add order

def require_step1(session: dict):
    if "step1" not in session:
        raise HTTPException(status_code=400, detail="請先完成第1步")

def require_step2(session: dict):
    if "step2" not in session:
        raise HTTPException(status_code=400, detail="請先完成第2步")

@router.get("/orders/new/step1", name="order_step1")
def get_step1(request: Request, commons=Depends(common_template_params)):
    return templates.TemplateResponse("add_order_step1.html", {**commons, "request": request})



@router.get("/orders/new/step2", name="order_step2")
def get_step2(request: Request, commons=Depends(common_template_params)):
    require_step1(request.session)
    return templates.TemplateResponse("add_order_step2.html", {**commons, "request": request})


@router.get("/orders/new/step3", name="order_step3")
def get_step3(request: Request, commons=Depends(common_template_params)):
    require_step1(request.session)
    require_step2(request.session)

    step1 = request.session["step1"]
    dishes = request.session["step2"]["dishes"]
    return templates.TemplateResponse(
        "add_order_step3.html",
        {
            **commons,
            "request": request,
            "step1": step1,
            "dishes": dishes,
        }
    )

# @router.get("/orders/new/step4", name="order_step4")
# def get_step4(request: Request):
#     return templates.TemplateResponse("add_order_step4.html", {
#       "request": request,
#     })

@router.get("/orders/new/step4", name="order_step4")
def get_step4(request: Request, commons=Depends(common_template_params)):
    require_step1(request.session)
    require_step2(request.session)

    # 從 session 拿出前面步驟的資料
    step1 = request.session["step1"]
    dishes = request.session["step2"]["dishes"]
    total = sum(d["dish_price"] * d["quantity"] for d in dishes)

    return templates.TemplateResponse(
        "add_order_step4.html",
        {
            **commons,
            "request": request,
            "step1": step1,
            "dishes": dishes,
            "total_price": total,
        }
    )

#Step1 POST
@router.post("/orders/new/step1")
def post_step1(
    request: Request,
    order_date: str    = Form(...),
    order_time: str    = Form(...),
    pickup_method: str = Form(...),
    address: str       = Form(None),
):

    data = Step1(
      order_date=order_date,
      order_time=order_time,
      pickup_method=pickup_method,
      address=address
    )
   
    request.session["step1"] = {
        "order_date":    data.order_date.isoformat(),
        "order_time":    data.order_time.isoformat(),
        "pickup_method": data.pickup_method,
        "address":       data.address,
    }
    return RedirectResponse(
        url="/customer/orders/new/step2",
        status_code=status.HTTP_302_FOUND
    )

#Step2 POST
@router.post("/orders/new/step2")
def post_step2(
    request: Request,
    dish_name:      List[str] = Form(...),
    quantity:       List[int] = Form(...),
    ingredients:    List[str] = Form([]),
    special_recipe: List[str] = Form([]),
    customer_note:  List[str] = Form([]),
    saltiness:      List[int] = Form(...),
    spiciness:      List[int] = Form(...),
    oiliness:       List[int] = Form(...),
    aroma:          List[int] = Form(...),
    dish_price:     List[int] = Form(...),
):
    require_step1(request.session)
    dishes = []
    for i in range(len(dish_name)):
        dishes.append({
            "dish_name":      dish_name[i],
            "quantity":       quantity[i],
            "ingredients":    ingredients[i],
            "special_recipe": special_recipe[i],
            "customer_note":  customer_note[i],
            "saltiness":      saltiness[i],
            "spiciness":      spiciness[i],
            "oiliness":       oiliness[i],
            "aroma":          aroma[i],
            "dish_price":     dish_price[i],
        })
    request.session["step2"] = Step2(dishes=dishes).dict()
    return RedirectResponse(url="/customer/orders/new/step3", status_code=status.HTTP_302_FOUND)

#Step3 POST
@router.post("/orders/new/step3")
def post_step3(request: Request):
    require_step1(request.session)
    require_step2(request.session)
    return RedirectResponse(url="/customer/orders/new/step4", status_code=status.HTTP_302_FOUND)

#Step4 POST
@router.post("/orders/new/step4")
def post_step4(
    request: Request,
    contact_phone: str = Form(...),
    db: Session        = Depends(get_db),
):

    if "step1" not in request.session or "step2" not in request.session:
        raise HTTPException(status_code=400, detail="資料不完整")

    oc = OrderCreate(
      step1=request.session["step1"],
      step2=request.session["step2"],
      step4={"contact_phone": contact_phone,
             "total_price": sum(d["dish_price"] for d in request.session["step2"]["dishes"])}
    )

    token = request.cookies.get("access_token")
    user = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user = db.query(User).get(payload["user_id"])

    new_order = OrderModel(
      order_date=oc.step1.order_date,
      order_time=oc.step1.order_time,
      pickup_method=oc.step1.pickup_method,
      address=oc.step1.address,
      contact_phone=oc.step4.contact_phone,
      total_price=oc.step4.total_price,
      customer_id   = user.id if user else None
    )
    db.add(new_order); db.commit(); db.refresh(new_order)

    for d in oc.step2.dishes:
        new_dish = DishModel(
          order_id=new_order.id,
          dish_name=d.dish_name,
          quantity=d.quantity,
          special_recipe=d.special_recipe,
          customer_note=d.customer_note,
          saltiness=d.saltiness,
          spiciness=d.spiciness,
          oiliness=d.oiliness,
          aroma=d.aroma,
          price=d.dish_price
        )
        db.add(new_dish); db.commit(); db.refresh(new_dish)
        for ing in (d.ingredients or "").split(","):
            if ing.strip():
                di = IngredientModel(dish_id=new_dish.id, ingredient_name=ing.strip())
                db.add(di)
        db.commit()

    for k in ("step1", "step2"):
        request.session.pop(k, None)

    return RedirectResponse(url="/customer/orders/list", status_code=status.HTTP_302_FOUND)



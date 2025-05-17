from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, time

from database import get_db
from models.order import Order, Dish, DishIngredient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/orders", name="customer_order_list")
def order_list_page(request: Request, db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return templates.TemplateResponse(
        "order_list.html",
        {"request": request, "orders": orders}
    )

@router.get("/orders/new", name="customer_order_new")
def new_order_page(request: Request):
    return templates.TemplateResponse(
        "order_new.html",
        {"request": request}
    )

@router.post("/orders/new", name="customer_order_create")
def create_order(
    request: Request,
    order_date: date = Form(...),
    order_time: time = Form(...),
    pickup_method: str = Form(...),
    address: str = Form(None),
    dish_name: list[str] = Form(...),
    quantity: list[int] = Form(...),
    special_recipe: list[str] = Form(None),
    customer_note: list[str] = Form(None),
    saltiness: list[int] = Form(None),
    spiciness: list[int] = Form(None),
    oiliness: list[int] = Form(None),
    aroma: list[int] = Form(None),
    ingredients: list[str] = Form(None),
    db: Session = Depends(get_db)
):

    new_order = Order(
        order_date=order_date,
        order_time=order_time,
        pickup_method=pickup_method,
        address=address
    )
    db.add(new_order); db.commit(); db.refresh(new_order)

    n = len(dish_name)
    if ingredients and len(ingredients) != n:
        raise HTTPException(400, "食材列表數量與菜品數不符")

    for i in range(n):
        d = Dish(
            order_id=new_order.id,
            dish_name=dish_name[i],
            quantity=quantity[i],
            special_recipe=(special_recipe[i] if special_recipe else None),
            customer_note=(customer_note[i] if customer_note else None),
            saltiness=(saltiness[i] if saltiness else None),
            spiciness=(spiciness[i] if spiciness else None),
            oiliness=(oiliness[i] if oiliness else None),
            aroma=(aroma[i] if aroma else None)
        )
        db.add(d); db.commit(); db.refresh(d)

        if ingredients:
            ing_names = [x.strip() for x in ingredients[i].split(',') if x.strip()]
            for name in ing_names:
                db.add(DishIngredient(dish_id=d.id, ingredient_name=name))
        db.commit()

    return RedirectResponse(
        url=request.url_for('customer_order_list'),
        status_code=status.HTTP_302_FOUND
    )
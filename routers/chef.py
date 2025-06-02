from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.order import Order, OrderStatus
from models.user import User
from utils.dependencies import require_chef, common_template_params

router = APIRouter(dependencies=[Depends(require_chef)])
templates = Jinja2Templates(directory="templates")

@router.get("/", name="chef_dashboard")
def chef_dashboard(
    request: Request,
    commons=Depends(common_template_params),
    current_user: User = Depends(require_chef),
    db: Session = Depends(get_db)
):
    # 獲取廚師的待接訂單
    pending_orders = db.query(Order).filter(
        Order.chef_id.is_(None),
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
            "request": request,
            "pending_orders": pending_orders,
            "my_orders": my_orders
        }
    )
    

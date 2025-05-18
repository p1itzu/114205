from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, time

from database import get_db
from models.order import Order, Dish, DishIngredient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", name="chef")
def chef():
    return "Chef"
    

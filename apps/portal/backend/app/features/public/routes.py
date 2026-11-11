from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Plan, User
from app.shared.http import current_user, render

router = APIRouter()

@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all()
    return render(request, "home.html", user, plans=plans)


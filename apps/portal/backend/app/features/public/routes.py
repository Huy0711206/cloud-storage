import re
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.models import Order, Plan, User
from app.core.security import hash_password, make_verify_token, read_verify_token, verify_password
from app.shared import mailer as emailer
from app.shared.http import current_user, dt, flash, render, require_user, require_admin
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.features.billing import service as services
from app.features.storage import service as storage_services
from app.features.payments import service as payment_services
from app.features.payments import vnpay

router = APIRouter()

@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all()
    return render(request, "home.html", user, plans=plans)


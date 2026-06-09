from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app import models
from app.utils.auth_utils import hash_password, verify_password, create_access_token

router    = APIRouter()
SETUP_KEY = "SETUP_ATTENDANCE_2024"   # pehli baar admin banane ke liye secret key

class AdminCreate(BaseModel):
    username:  str
    email:     EmailStr
    password:  str
    setup_key: str

@router.post("/setup")
def setup_admin(payload: AdminCreate, db: Session = Depends(get_db)):
    """Pehli baar admin account banana — setup_key se protect hai"""
    if payload.setup_key != SETUP_KEY:
        raise HTTPException(403, "Invalid setup key")
    if db.query(models.Admin).filter(models.Admin.username == payload.username).first():
        raise HTTPException(400, "Admin already exists")
    admin = models.Admin(
        username   = payload.username,
        email      = payload.email,
        hashed_pwd = hash_password(payload.password),
    )
    db.add(admin); db.commit(); db.refresh(admin)
    return {"message": "Admin created", "username": admin.username}

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == form.username).first()
    if not admin or not verify_password(form.password, admin.hashed_pwd):
        raise HTTPException(401, "Wrong username or password")
    token = create_access_token({"sub": admin.username})
    return {"access_token": token, "token_type": "bearer", "admin_name": admin.username}

@router.get("/me")
def get_me(db: Session = Depends(get_db), admin=Depends(__import__('app.utils.auth_utils', fromlist=['get_current_admin']).get_current_admin)):
    return {"id": admin.id, "username": admin.username, "email": admin.email}
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import models
from app.utils.auth_utils import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)

router = APIRouter()


class AdminCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    setup_key: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value):
            raise ValueError("Password must include upper and lowercase letters")
        if not re.search(r"\d", value):
            raise ValueError("Password must include a digit")
        if not re.search(r"[!@#$%^&*]", value):
            raise ValueError("Password must include a special character")
        return value


class CredentialsChange(BaseModel):
    current_password: str
    new_password: str
    new_username: str | None = None

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("New password must be at least 12 characters")
        if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value):
            raise ValueError("New password must include upper and lowercase letters")
        if not re.search(r"\d", value):
            raise ValueError("New password must include a digit")
        if not re.search(r"[!@#$%^&*]", value):
            raise ValueError("New password must include a special character")
        return value

    @field_validator("new_username")
    @classmethod
    def validate_new_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value.lower() in {"admin", "root", "administrator"}:
            raise ValueError("Username is too common")
        if len(value) < 6:
            raise ValueError("Username must be at least 6 characters")
        return value


@router.post("/setup")
def setup_admin(payload: AdminCreate, db: Session = Depends(get_db)):
    """First-time admin only — blocked after any admin exists."""
    if payload.setup_key != settings.SETUP_KEY:
        raise HTTPException(403, "Invalid setup key")
    if db.query(models.Admin).count() > 0:
        raise HTTPException(403, "Setup disabled — admin already exists")
    if db.query(models.Admin).filter(models.Admin.username == payload.username).first():
        raise HTTPException(400, "Username already taken")

    admin = models.Admin(
        username=payload.username,
        email=payload.email,
        hashed_pwd=hash_password(payload.password),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"message": "Admin created", "username": admin.username}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == form.username).first()
    if not admin or not verify_password(form.password, admin.hashed_pwd):
        raise HTTPException(401, "Wrong username or password")
    token = create_access_token({"sub": admin.username})
    return {"access_token": token, "token_type": "bearer", "admin_name": admin.username}


@router.post("/change-credentials")
def change_credentials(
    payload: CredentialsChange,
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(get_current_admin),
):
    if not verify_password(payload.current_password, admin.hashed_pwd):
        raise HTTPException(400, "Current password is incorrect")

    if payload.new_username and payload.new_username != admin.username:
        taken = (
            db.query(models.Admin)
            .filter(models.Admin.username == payload.new_username, models.Admin.id != admin.id)
            .first()
        )
        if taken:
            raise HTTPException(400, "Username already taken")
        admin.username = payload.new_username

    admin.hashed_pwd = hash_password(payload.new_password)
    db.commit()
    db.refresh(admin)
    return {"message": "Credentials updated", "username": admin.username}


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(get_current_admin),
):
    return {"id": admin.id, "username": admin.username, "email": admin.email}

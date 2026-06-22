from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
import base64
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app import models
from app.utils.auth_utils import get_current_admin
from app.utils.face_utils import build_profile, find_duplicate, extract_embedding

router = APIRouter()

class EmployeeCreate(BaseModel):
    name:        str
    employee_id: str
    department:  Optional[str] = None
    face_image:  Optional[str] = None         # single sample (backward compatible)
    face_images: Optional[List[str]] = None   # multiple samples (preferred)

class EmployeeUpdate(BaseModel):
    name:        Optional[str] = None
    employee_id: Optional[str] = None
    department:  Optional[str] = None
    face_image:  Optional[str] = None
    face_images: Optional[List[str]] = None


def _collect_images(face_image, face_images) -> List[str]:
    imgs = list(face_images) if face_images else []
    if face_image:
        imgs.append(face_image)
    return [i for i in imgs if i]


def _load_face_encodings(db):
    emps = db.query(models.Employee).filter(models.Employee.face_encoding != None).all()
    return [(e.id, e.face_encoding) for e in emps]


def _build_encoding(images: List[str], db, exclude_emp_id=None) -> bytes:
    """Turn enrollment photos into geometry-only face profile, or raise 422."""
    face_bytes, err = build_profile(images)
    if face_bytes is None:
        raise HTTPException(422, err or "No face detected in the captured photos. Please try again.")

    stored = _load_face_encodings(db)
    for img in images:
        emb, _ = extract_embedding(img)
        if emb is None:
            continue
        dup_id = find_duplicate(emb, stored, exclude_emp_id=exclude_emp_id)
        if dup_id is not None:
            dup = db.query(models.Employee).filter(models.Employee.id == dup_id).first()
            name = dup.name if dup else "another employee"
            raise HTTPException(409, f"This face is already registered as {name}.")
    return face_bytes


@router.post("/register")
async def register_employee(
    name: str = Form(...),
    employee_id: str = Form(...),
    department: str = Form(""),
    face_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    name = name.strip()
    employee_id = employee_id.strip()
    department = department.strip() or None

    if not name or not employee_id:
        raise HTTPException(422, "Name and Employee ID are required.")

    if db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first():
        raise HTTPException(400, "This Employee ID is already registered.")

    raw = await face_image.read()
    if not raw:
        raise HTTPException(422, "Face photo is required.")
    if len(raw) > 600_000:
        raise HTTPException(422, "Photo is too large. Move closer to the camera and try again.")

    b64 = f"data:{face_image.content_type or 'image/jpeg'};base64,{base64.b64encode(raw).decode('ascii')}"
    images = [b64]
    face_bytes = _build_encoding(images, db)

    emp = models.Employee(
        name          = name,
        employee_id   = employee_id,
        department    = department,
        face_encoding = face_bytes,
        registered_by = admin.id,
    )
    db.add(emp); db.commit(); db.refresh(emp)
    return {"message": "Employee registered successfully", "name": emp.name, "id": emp.id}

@router.get("/")
def list_employees(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    emps = db.query(models.Employee).all()
    return [{
        "id": e.id, "name": e.name, "employee_id": e.employee_id,
        "department": e.department, "is_active": e.is_active,
        "registered_at": e.registered_at.isoformat() if e.registered_at else None
    } for e in emps]

@router.patch("/{employee_id}")
def update_employee(employee_id: str, payload: EmployeeUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    emp = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    if payload.employee_id and payload.employee_id != emp.employee_id:
        clash = db.query(models.Employee).filter(models.Employee.employee_id == payload.employee_id).first()
        if clash:
            raise HTTPException(400, "Another employee already uses this Employee ID.")
        emp.employee_id = payload.employee_id

    if payload.name is not None:
        emp.name = payload.name
    if payload.department is not None:
        emp.department = payload.department

    images = _collect_images(payload.face_image, payload.face_images)
    if images:
        emp.face_encoding = _build_encoding(images, db, exclude_emp_id=emp.id)

    db.commit(); db.refresh(emp)
    return {
        "message": "Employee updated successfully",
        "id": emp.id, "name": emp.name, "employee_id": emp.employee_id,
        "department": emp.department, "is_active": emp.is_active,
    }

@router.patch("/{employee_id}/deactivate")
def deactivate(employee_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    emp = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    emp.is_active = False; db.commit()
    return {"message": f"{emp.name} deactivated"}

@router.patch("/{employee_id}/activate")
def activate(employee_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    emp = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    emp.is_active = True; db.commit()
    return {"message": f"{emp.name} reactivated"}

@router.delete("/{employee_id}")
def delete_employee(employee_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    emp = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    db.query(models.AttendanceLog).filter(models.AttendanceLog.employee_id == emp.id).delete()
    db.delete(emp); db.commit()
    return {"message": f"{emp.name} deleted permanently"}

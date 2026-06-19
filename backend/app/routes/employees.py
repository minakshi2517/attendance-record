from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app import models
from app.utils.auth_utils import get_current_admin
from app.utils.face_utils import encode_face

router = APIRouter()

class EmployeeCreate(BaseModel):
    name:        str
    employee_id: str
    department:  Optional[str] = None
    face_image:  str            # base64 image captured from the admin camera

class EmployeeUpdate(BaseModel):
    name:        Optional[str] = None
    employee_id: Optional[str] = None
    department:  Optional[str] = None
    face_image:  Optional[str] = None   # optional: re-capture face

@router.post("/register")
def register_employee(payload: EmployeeCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if db.query(models.Employee).filter(models.Employee.employee_id == payload.employee_id).first():
        raise HTTPException(400, "This Employee ID is already registered.")
    face_bytes, face_err = encode_face(payload.face_image)
    if face_bytes is None:
        raise HTTPException(422, face_err or "No face detected. Face the camera directly and capture again.")
    emp = models.Employee(
        name          = payload.name,
        employee_id   = payload.employee_id,
        department    = payload.department,
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

    if payload.face_image:
        face_bytes, face_err = encode_face(payload.face_image)
        if face_bytes is None:
            raise HTTPException(422, face_err or "No face detected. Face the camera directly and capture again.")
        emp.face_encoding = face_bytes

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

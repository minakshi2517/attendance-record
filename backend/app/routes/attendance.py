from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app import models
from app.utils.auth_utils import get_current_admin
from app.utils.face_utils import match_face
from app.config import settings

router = APIRouter()

class FaceRequest(BaseModel):
    image: str   # base64

def load_encodings(db):
    """Saare active employees ke face encodings load karo DB se"""
    emps = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.face_encoding != None
    ).all()
    return [(e.id, e.face_encoding) for e in emps]

@router.post("/checkin")
def check_in(payload: FaceRequest, db: Session = Depends(get_db)):
    encodings = load_encodings(db)
    if not encodings:
        raise HTTPException(404, "Koi registered employee nahi hai")

    emp_id, confidence = match_face(payload.image, encodings)
    if emp_id is None:
        raise HTTPException(401, "Face recognize nahi hua. Dobara try karo.")

    emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()

    # Aaj pehle se check-in hai kya?
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.employee_id == emp_id,
        models.AttendanceLog.check_in >= today,
        models.AttendanceLog.check_out == None,
    ).first()

    if existing:
        return {
            "status": "already_checked_in",
            "message": f"{emp.name} pehle se check-in hai",
            "check_in_time": existing.check_in.isoformat(),
        }

    now = datetime.now(timezone.utc)
    log = models.AttendanceLog(employee_id=emp_id, check_in=now, confidence=confidence)
    db.add(log); db.commit(); db.refresh(log)
    return {
        "status": "checked_in",
        "message": f"Welcome, {emp.name}!",
        "employee": {"name": emp.name, "employee_id": emp.employee_id, "department": emp.department},
        "check_in_time": now.isoformat(),
        "confidence": confidence,
    }

@router.post("/checkout")
def check_out(payload: FaceRequest, db: Session = Depends(get_db)):
    encodings = load_encodings(db)
    if not encodings:
        raise HTTPException(404, "Koi registered employee nahi hai")

    emp_id, confidence = match_face(payload.image, encodings)
    if emp_id is None:
        raise HTTPException(401, "Face recognize nahi hua. Dobara try karo.")

    emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    log   = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.employee_id == emp_id,
        models.AttendanceLog.check_in >= today,
        models.AttendanceLog.check_out == None,
    ).first()

    if not log:
        raise HTTPException(400, "Pehle check-in karo!")

    # ⏱ 15 MINUTE RULE
    now           = datetime.now(timezone.utc)
    lockout_until = log.check_in + timedelta(minutes=settings.CHECKOUT_LOCKOUT_MINUTES)
    if now < lockout_until:
        remaining = int((lockout_until - now).total_seconds())
        mins      = remaining // 60
        secs      = remaining % 60
        raise HTTPException(403, f"Check-out nahi ho sakta. {mins}m {secs}s aur ruko.")

    log.check_out = now; db.commit()
    d = now - log.check_in
    hours, mins = int(d.total_seconds()//3600), int((d.total_seconds()%3600)//60)
    return {
        "status": "checked_out",
        "message": f"Goodbye, {emp.name}! Aaj {hours}h {mins}m kaam kiya.",
        "check_in_time": log.check_in.isoformat(),
        "check_out_time": now.isoformat(),
        "duration": f"{hours}h {mins}m",
        "confidence": confidence,
    }

@router.get("/today")
def today_attendance(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    logs  = db.query(models.AttendanceLog, models.Employee)\
              .join(models.Employee)\
              .filter(models.AttendanceLog.check_in >= today)\
              .order_by(models.AttendanceLog.check_in.desc()).all()
    result = []
    for log, emp in logs:
        dur = None
        if log.check_out:
            d = log.check_out - log.check_in
            dur = f"{int(d.total_seconds()//3600)}h {int((d.total_seconds()%3600)//60)}m"
        result.append({
            "employee_name": emp.name, "employee_id": emp.employee_id,
            "department": emp.department,
            "check_in": log.check_in.isoformat() if log.check_in else None,
            "check_out": log.check_out.isoformat() if log.check_out else None,
            "duration": dur,
            "status": "Present" if log.check_out else "Office mein hai",
            "confidence": log.confidence,
        })
    return result

@router.get("/history")
def history(
    employee_id: Optional[str] = None,
    date_from:   Optional[str] = None,
    date_to:     Optional[str] = None,
    db:          Session       = Depends(get_db),
    admin        = Depends(get_current_admin),
):
    q = db.query(models.AttendanceLog, models.Employee).join(models.Employee)
    if employee_id:
        q = q.filter(models.Employee.employee_id == employee_id)
    if date_from:
        q = q.filter(models.AttendanceLog.check_in >= datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc))
    if date_to:
        dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
        q  = q.filter(models.AttendanceLog.check_in <= dt)
    logs = q.order_by(models.AttendanceLog.check_in.desc()).limit(500).all()
    result = []
    for log, emp in logs:
        dur = None
        if log.check_out:
            d   = log.check_out - log.check_in
            dur = f"{int(d.total_seconds()//3600)}h {int((d.total_seconds()%3600)//60)}m"
        result.append({
            "employee_name": emp.name, "employee_id": emp.employee_id,
            "department": emp.department,
            "check_in":  log.check_in.isoformat()  if log.check_in  else None,
            "check_out": log.check_out.isoformat() if log.check_out else None,
            "duration": dur,
            "status": "Present" if log.check_out else "Office mein hai",
        })
    return result

@router.get("/stats")
def stats(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    today        = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total        = db.query(models.Employee).filter(models.Employee.is_active == True).count()
    checked_in   = db.query(models.AttendanceLog).filter(models.AttendanceLog.check_in >= today).count()
    currently_in = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.check_in >= today,
        models.AttendanceLog.check_out == None
    ).count()
    return {
        "total_active_employees": total,
        "checked_in_today":       checked_in,
        "currently_in_office":    currently_in,
        "absent_today":           total - checked_in,
    }
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app import models
from app.utils.auth_utils import get_current_admin
from app.utils.face_utils import match_face, match_face_bytes
from app.config import settings
from app.utils.time_utils import today_start_utc, now_utc, checkout_available_at, to_iso, local_date_to_utc_start, local_date_to_utc_end

router = APIRouter()

class FaceRequest(BaseModel):
    image: str

MATCH_ERRORS = {
    "no_face":          "No face detected. Look straight at the camera.",
    "multiple_faces":   "Only one person should be in the frame.",
    "face_too_small":   "Move closer to the camera.",
    "too_blurry":       "Hold still — image is too blurry.",
    "no_match":         "Face not recognized. Look straight at the camera, move closer, or ask admin to re-register you.",
    "outdated_profile": "Your face profile is outdated. Ask admin to re-register you.",
    "ambiguous":        "Could not identify you clearly. Please try again.",
    "error":            "Face scan failed. Please try again.",
}

def load_encodings(db):
    emps = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.face_encoding != None
    ).all()
    return [(e.id, e.face_encoding) for e in emps]

def _identify(payload: FaceRequest, db: Session):
    encodings = load_encodings(db)
    if not encodings:
        raise HTTPException(404, "No registered employees found. Ask admin to register team members first.")

    emp_id, confidence, reason = match_face(payload.image, encodings)
    if emp_id is None:
        raise HTTPException(403, MATCH_ERRORS.get(reason or "no_match", MATCH_ERRORS["no_match"]))

    emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()
    return emp, confidence


async def _read_face_uploads(primary: UploadFile, *extras: Optional[UploadFile]) -> List[bytes]:
    raws = [await primary.read()]
    for f in extras:
        if f is not None:
            chunk = await f.read()
            if chunk:
                raws.append(chunk)
    return [r for r in raws if r]


def _checkout_meta(check_in: datetime) -> dict:
    available = checkout_available_at(check_in)
    return {
        "checkout_lockout_minutes": settings.CHECKOUT_LOCKOUT_MINUTES,
        "checkout_available_at": to_iso(available),
        "timezone": settings.TIMEZONE,
    }


async def _identify_upload(face_image: UploadFile, db: Session, *extras: Optional[UploadFile]):
    encodings = load_encodings(db)
    if not encodings:
        raise HTTPException(404, "No registered employees found. Ask admin to register team members first.")

    raws = await _read_face_uploads(face_image, *extras)
    if not raws:
        raise HTTPException(422, "Face photo is required.")

    emp_id, confidence, reason = match_face_bytes(raws, encodings)
    if emp_id is None:
        raise HTTPException(403, MATCH_ERRORS.get(reason or "no_match", MATCH_ERRORS["no_match"]))

    emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()
    return emp, confidence

@router.post("/checkin")
async def check_in(
    face_image: UploadFile = File(...),
    face_image_2: Optional[UploadFile] = File(None),
    face_image_3: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    emp, confidence = await _identify_upload(face_image, db, face_image_2, face_image_3)

    today = today_start_utc()
    existing = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.employee_id == emp.id,
        models.AttendanceLog.check_in >= today,
        models.AttendanceLog.check_out == None,
    ).first()

    if existing:
        return {
            "status": "already_checked_in",
            "message": f"{emp.name} is already checked in.",
            "check_in_time": to_iso(existing.check_in),
            **_checkout_meta(existing.check_in),
        }

    now = now_utc()
    log = models.AttendanceLog(employee_id=emp.id, check_in=now, confidence=confidence)
    db.add(log); db.commit(); db.refresh(log)
    return {
        "status": "checked_in",
        "message": f"Welcome, {emp.name}!",
        "employee": {"name": emp.name, "employee_id": emp.employee_id, "department": emp.department},
        "check_in_time": to_iso(now),
        "confidence": confidence,
        **_checkout_meta(now),
    }

@router.post("/checkout")
async def check_out(
    face_image: UploadFile = File(...),
    face_image_2: Optional[UploadFile] = File(None),
    face_image_3: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    emp, confidence = await _identify_upload(face_image, db, face_image_2, face_image_3)

    today = today_start_utc()
    log   = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.employee_id == emp.id,
        models.AttendanceLog.check_in >= today,
        models.AttendanceLog.check_out == None,
    ).first()

    if not log:
        raise HTTPException(400, "Please check in first.")

    now           = now_utc()
    lockout_until = checkout_available_at(log.check_in)
    if now < lockout_until:
        remaining = int((lockout_until - now).total_seconds())
        mins      = remaining // 60
        secs      = remaining % 60
        raise HTTPException(403, f"Too early to check out. Please wait {mins}m {secs}s more.")

    log.check_out = now; db.commit()
    d = now - log.check_in
    hours, mins = int(d.total_seconds()//3600), int((d.total_seconds()%3600)//60)
    return {
        "status": "checked_out",
        "message": f"Goodbye, {emp.name}! You worked {hours}h {mins}m today.",
        "check_in_time": to_iso(log.check_in),
        "check_out_time": to_iso(now),
        "duration": f"{hours}h {mins}m",
        "confidence": confidence,
        "timezone": settings.TIMEZONE,
    }

@router.get("/today")
def today_attendance(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    today = today_start_utc()
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
            "check_in": to_iso(log.check_in) if log.check_in else None,
            "check_out": to_iso(log.check_out) if log.check_out else None,
            "duration": dur,
            "status": "Completed" if log.check_out else "In Office",
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
        q = q.filter(models.AttendanceLog.check_in >= local_date_to_utc_start(date_from))
    if date_to:
        q = q.filter(models.AttendanceLog.check_in <= local_date_to_utc_end(date_to))
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
            "check_in":  to_iso(log.check_in)  if log.check_in  else None,
            "check_out": to_iso(log.check_out) if log.check_out else None,
            "duration": dur,
            "status": "Completed" if log.check_out else "In Office",
        })
    return result

@router.get("/stats")
def stats(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    today        = today_start_utc()
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

import threading
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.routes import auth, employees, attendance
from app.utils.face_utils import warmup_model
from app.config import settings

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(attendance.router,prefix="/api/attendance",tags=["Attendance"])


@app.on_event("startup")
def _startup():
    _ensure_default_admin()
    threading.Thread(target=warmup_model, daemon=True).start()


def _ensure_default_admin():
    """After HF rebuild the DB is empty — recreate admin automatically."""
    from app import models
    from app.utils.auth_utils import hash_password

    db = SessionLocal()
    try:
        if db.query(models.Admin).count() == 0:
            db.add(models.Admin(
                username   = settings.DEFAULT_ADMIN_USER,
                email      = settings.DEFAULT_ADMIN_EMAIL,
                hashed_pwd = hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            ))
            db.commit()
            logger.info("Default admin account created")
    except Exception as e:
        logger.warning("Admin bootstrap failed: %s", e)
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "Face Attendance API running"}


@app.get("/health")
def health():
    return {"ok": True}

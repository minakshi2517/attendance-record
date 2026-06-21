import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import auth, employees, attendance
from app.utils.face_utils import warmup_model

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
def _warmup_in_background():
    # Load the face model in a background thread so the server can start
    # serving immediately (the first face request will wait if needed).
    threading.Thread(target=warmup_model, daemon=True).start()


@app.get("/")
def root():
    return {"status": "Face Attendance API running"}


@app.get("/health")
def health():
    return {"ok": True}

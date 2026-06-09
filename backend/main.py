from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import auth, employees, attendance
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(attendance.router,prefix="/api/attendance",tags=["Attendance"])

@app.get("/")
def root():
    return {"status": "Face Attendance API running"}
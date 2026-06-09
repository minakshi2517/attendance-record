from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Admin(Base):
    __tablename__ = "admins"
    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, index=True, nullable=False)
    email      = Column(String, unique=True, index=True, nullable=False)
    hashed_pwd = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Employee(Base):
    __tablename__ = "employees"
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    employee_id   = Column(String, unique=True, index=True, nullable=False)
    department    = Column(String, nullable=True)
    face_encoding = Column(LargeBinary, nullable=True)  # face ka data bytes mein
    is_active     = Column(Boolean, default=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    registered_by = Column(Integer, ForeignKey("admins.id"))
    attendance_logs = relationship("AttendanceLog", back_populates="employee")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    check_in    = Column(DateTime(timezone=True), nullable=True)
    check_out   = Column(DateTime(timezone=True), nullable=True)
    date        = Column(DateTime(timezone=True), server_default=func.now())
    confidence  = Column(Float, nullable=True)   # face match % kitna
    employee    = relationship("Employee", back_populates="attendance_logs")
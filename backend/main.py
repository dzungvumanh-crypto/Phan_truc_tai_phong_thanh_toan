"""
FastAPI backend — Phân lịch trực Phòng Thanh toán
Port: 8001
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import APP_TITLE, API_PREFIX
from backend.database import engine, SessionLocal
from backend.models.duty_models import (   # noqa: F401 — ensure tables registered
    Staff, Absence, DutyRequest, SpecialDay,
    RotationState, DutyShift, DutyShiftNV, ShiftConfig
)
from backend.models.duty_models import Base
from backend.services.schedule_service import startup_init
from backend.routers import staff, constraints, schedule, stats, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        startup_init(db)
    finally:
        db.close()
    yield
    # ── Shutdown (nothing needed) ─────────────────────────────


app = FastAPI(
    title=APP_TITLE,
    version="1.0.0",
    description="API phân lịch trực Phòng Thanh toán Agribank TTTT",
    lifespan=lifespan,
)

# CORS — cho phép frontend NiceGUI gọi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(staff.router,       prefix=API_PREFIX)
app.include_router(constraints.router, prefix=API_PREFIX)
app.include_router(schedule.router,    prefix=API_PREFIX)
app.include_router(stats.router,       prefix=API_PREFIX)
app.include_router(export.router,      prefix=API_PREFIX)


@app.get("/")
def root():
    return {"message": APP_TITLE, "docs": "/docs"}

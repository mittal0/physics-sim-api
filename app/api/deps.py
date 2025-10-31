from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.job_service import JobService


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    """Dependency to get job service"""
    return JobService(db)
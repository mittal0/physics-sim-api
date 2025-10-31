import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR

from app.core.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as
    stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class JobStatus(str, Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job model for storing simulation job metadata"""
    
    __tablename__ = "jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    status = Column(String(20), default=JobStatus.QUEUED, nullable=False, index=True)
    
    # Job configuration
    container_image = Column(String(255), nullable=False)
    command = Column(Text, nullable=True)
    params = Column(JSON, nullable=False, default=dict)
    metadata = Column(JSON, nullable=True, default=dict)
    
    # User information
    created_by = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Execution details
    logs = Column(Text, nullable=True, default="")
    result_path = Column(String(500), nullable=True)
    exit_code = Column(Integer, nullable=True)
    runtime_seconds = Column(Float, nullable=True)
    
    # Resource limits (stored as JSON for flexibility)
    resource_limits = Column(JSON, nullable=True, default=dict)
    
    # Parent job for sweep operations
    parent_job_id = Column(GUID(), nullable=True, index=True)
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status={self.status})>"
    
    @property
    def is_terminal(self) -> bool:
        """Check if job is in terminal state"""
        return self.status in [JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status == JobStatus.RUNNING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation"""
        return {
            "id": str(self.id),
            "status": self.status,
            "container_image": self.container_image,
            "command": self.command,
            "params": self.params,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "logs": self.logs,
            "result_path": self.result_path,
            "exit_code": self.exit_code,
            "runtime_seconds": self.runtime_seconds,
            "resource_limits": self.resource_limits,
            "parent_job_id": str(self.parent_job_id) if self.parent_job_id else None,
        }
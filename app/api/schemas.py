from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class JobParams(BaseModel):
    """Base schema for job parameters"""
    
    class Config:
        extra = "allow"  # Allow additional parameters


class JobMetadata(BaseModel):
    """Base schema for job metadata"""
    
    project: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    
    class Config:
        extra = "allow"  # Allow additional metadata


class JobCreate(BaseModel):
    """Schema for creating a new job"""
    
    container_image: Optional[str] = Field(
        None,
        description="Docker image to use for the simulation"
    )
    command: Optional[str] = Field(
        None,
        description="Command to run inside the container"
    )
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters for the simulation"
    )
    sweep: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of parameter sets for parameter sweep"
    )
    metadata: Optional[JobMetadata] = Field(
        default_factory=JobMetadata,
        description="Additional metadata for the job"
    )
    created_by: Optional[str] = Field(
        None,
        description="User who created the job"
    )
    
    @validator("sweep")
    def validate_sweep(cls, v, values):
        """Ensure sweep and params are not both provided"""
        if v is not None and values.get("params"):
            raise ValueError("Cannot specify both 'params' and 'sweep'")
        return v


class JobResponse(BaseModel):
    """Schema for job response"""
    
    id: UUID
    status: str
    container_image: str
    command: Optional[str]
    params: Dict[str, Any]
    metadata: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    logs: Optional[str]
    result_path: Optional[str]
    exit_code: Optional[int]
    runtime_seconds: Optional[float]
    resource_limits: Optional[Dict[str, Any]]
    parent_job_id: Optional[UUID]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list response"""
    
    jobs: List[JobResponse]
    total: int
    page: int
    size: int
    has_next: bool


class JobCreateResponse(BaseModel):
    """Schema for job creation response"""
    
    jobs: List[UUID] = Field(description="List of created job IDs")
    sweep_mapping: Optional[Dict[str, UUID]] = Field(
        None,
        description="Mapping of parameter sets to job IDs for sweeps"
    )


class JobLogsResponse(BaseModel):
    """Schema for job logs response"""
    
    job_id: UUID
    logs: str
    last_updated: datetime


class HealthResponse(BaseModel):
    """Schema for health check response"""
    
    status: str
    timestamp: datetime
    services: Dict[str, str] = Field(
        description="Status of dependent services"
    )


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    
    error: str
    detail: Optional[str] = None
    timestamp: datetime


class JobStatsResponse(BaseModel):
    """Schema for job statistics response"""
    
    total_jobs: int
    jobs_by_status: Dict[str, int]
    avg_runtime_seconds: Optional[float]
    success_rate: float
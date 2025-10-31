import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_job_service
from app.api.schemas import (
    JobCreate,
    JobCreateResponse,
    JobResponse,
    JobListResponse,
    JobLogsResponse,
    JobStatsResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.job import JobStatus
from app.services.job_service import JobService
from app.tasks.simulation import run_simulation

logger = get_logger(__name__)
router = APIRouter()


@router.post("/jobs", response_model=JobCreateResponse)
async def create_jobs(
    job_data: JobCreate,
    job_service: JobService = Depends(get_job_service),
) -> JobCreateResponse:
    """Create one or more simulation jobs"""
    try:
        job_ids = job_service.create_job(job_data)
        
        # Submit jobs to Celery
        for job_id in job_ids:
            run_simulation.delay(str(job_id))
        
        # For sweep jobs, create mapping of parameter sets to job IDs
        sweep_mapping = None
        if job_data.sweep:
            sweep_mapping = {}
            for i, param_set in enumerate(job_data.sweep):
                param_key = f"params_{i}"
                sweep_mapping[param_key] = job_ids[i]
        
        logger.info("Created and queued jobs", job_ids=[str(jid) for jid in job_ids])
        
        return JobCreateResponse(
            jobs=job_ids,
            sweep_mapping=sweep_mapping,
        )
    
    except Exception as e:
        logger.error("Failed to create jobs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Get job by ID"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    job_service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """List jobs with pagination and filtering"""
    return job_service.list_jobs(
        page=page,
        size=size,
        status=status,
        created_by=created_by,
    )


@router.get("/jobs/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobLogsResponse:
    """Get job logs"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobLogsResponse(
        job_id=job_id,
        logs=job.logs or "",
        last_updated=job.started_at or job.created_at,
    )


@router.get("/jobs/{job_id}/logs/stream")
async def stream_job_logs(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
):
    """Stream job logs (Server-Sent Events)"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    def generate_logs():
        """Generate log events"""
        # This is a simplified implementation
        # In production, you'd want to implement proper SSE streaming
        # with periodic updates from the database or log files
        yield f"data: {job.logs or ''}\n\n"
        
        # If job is not terminal, could implement periodic updates
        if not job.is_terminal:
            yield f"data: Job is still running...\n\n"
    
    return StreamingResponse(
        generate_logs(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/jobs/{job_id}/result")
async def download_job_result(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
):
    """Download job result artifact"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.result_path:
        raise HTTPException(status_code=404, detail="Job result not available")
    
    if not os.path.exists(job.result_path):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # For directories, create a zip file
    if os.path.isdir(job.result_path):
        import zipfile
        import tempfile
        
        # Create temporary zip file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(job.result_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, job.result_path)
                        zipf.write(file_path, arcname)
            
            return FileResponse(
                tmp_file.name,
                media_type="application/zip",
                filename=f"job_{job_id}_results.zip",
            )
    else:
        # Return single file
        return FileResponse(job.result_path)


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Cancel a running job"""
    job = job_service.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # TODO: Implement actual container cancellation via Docker API
    # This would involve stopping the running container
    
    logger.info("Job cancellation requested", job_id=str(job_id))
    return JobResponse.from_orm(job)


@router.get("/jobs/stats", response_model=JobStatsResponse)
async def get_job_stats(
    job_service: JobService = Depends(get_job_service),
) -> JobStatsResponse:
    """Get job statistics"""
    stats = job_service.get_job_stats()
    return JobStatsResponse(**stats)
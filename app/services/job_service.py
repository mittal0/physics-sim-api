import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.config import settings
from app.core.logging import get_logger
from app.models.job import Job, JobStatus
from app.api.schemas import JobCreate, JobResponse, JobListResponse

logger = get_logger(__name__)


class JobService:
    """Service for managing simulation jobs"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(self, job_data: JobCreate) -> List[UUID]:
        """Create one or more jobs based on job data
        
        Returns list of job IDs created
        """
        if job_data.sweep:
            return self._create_sweep_jobs(job_data)
        else:
            return [self._create_single_job(job_data)]

    def _create_single_job(self, job_data: JobCreate) -> UUID:
        """Create a single job"""
        job_id = uuid.uuid4()
        
        # Set default container image and command if not provided
        container_image = job_data.container_image or settings.default_container_image
        command = job_data.command
        
        # If command is not provided, build default command from params
        if not command and job_data.params:
            command = self._build_command_from_params(job_data.params)
        
        # Create job record
        job = Job(
            id=job_id,
            status=JobStatus.QUEUED,
            container_image=container_image,
            command=command,
            params=job_data.params or {},
            metadata=job_data.metadata.dict() if job_data.metadata else {},
            created_by=job_data.created_by,
            created_at=datetime.utcnow(),
            resource_limits={
                "cpu_limit": settings.default_cpu_limit,
                "memory_limit": settings.default_memory_limit,
            }
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info("Created job", job_id=str(job_id), status=job.status)
        return job_id

    def _create_sweep_jobs(self, job_data: JobCreate) -> List[UUID]:
        """Create multiple jobs for parameter sweep"""
        if not job_data.sweep:
            raise ValueError("Sweep data is required for sweep jobs")
        
        parent_job_id = uuid.uuid4()
        job_ids = []
        
        for param_set in job_data.sweep:
            job_id = uuid.uuid4()
            
            # Set default container image
            container_image = job_data.container_image or settings.default_container_image
            
            # Build command from parameters if not provided
            command = job_data.command
            if not command:
                command = self._build_command_from_params(param_set)
            
            # Create job record for this parameter set
            job = Job(
                id=job_id,
                status=JobStatus.QUEUED,
                container_image=container_image,
                command=command,
                params=param_set,
                metadata=job_data.metadata.dict() if job_data.metadata else {},
                created_by=job_data.created_by,
                created_at=datetime.utcnow(),
                parent_job_id=parent_job_id,
                resource_limits={
                    "cpu_limit": settings.default_cpu_limit,
                    "memory_limit": settings.default_memory_limit,
                }
            )
            
            self.db.add(job)
            job_ids.append(job_id)
        
        self.db.commit()
        
        logger.info(
            "Created sweep jobs",
            parent_job_id=str(parent_job_id),
            num_jobs=len(job_ids)
        )
        return job_ids

    def _build_command_from_params(self, params: Dict[str, Any]) -> str:
        """Build command string from parameters"""
        base_command = "python /sim/run_sim.py"
        param_args = []
        
        for key, value in params.items():
            param_args.append(f"--{key} {value}")
        
        if param_args:
            return f"{base_command} {' '.join(param_args)}"
        return base_command

    def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID"""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def list_jobs(
        self,
        page: int = 1,
        size: int = 50,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> JobListResponse:
        """List jobs with pagination and filtering"""
        query = self.db.query(Job)
        
        # Apply filters
        if status:
            query = query.filter(Job.status == status)
        if created_by:
            query = query.filter(Job.created_by == created_by)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(size).all()
        
        # Check if there are more pages
        has_next = total > (page * size)
        
        return JobListResponse(
            jobs=[JobResponse.from_orm(job) for job in jobs],
            total=total,
            page=page,
            size=size,
            has_next=has_next,
        )

    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        exit_code: Optional[int] = None,
        result_path: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and metadata"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.status = status
        
        if started_at:
            job.started_at = started_at
        
        if finished_at:
            job.finished_at = finished_at
            if job.started_at:
                job.runtime_seconds = (finished_at - job.started_at).total_seconds()
        
        if exit_code is not None:
            job.exit_code = exit_code
        
        if result_path:
            job.result_path = result_path
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(
            "Updated job status",
            job_id=str(job_id),
            status=status,
            exit_code=exit_code
        )
        return job

    def append_job_logs(self, job_id: UUID, logs: str) -> Optional[Job]:
        """Append logs to job"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        if job.logs:
            job.logs += logs
        else:
            job.logs = logs
        
        self.db.commit()
        return job

    def cancel_job(self, job_id: UUID) -> Optional[Job]:
        """Cancel a job"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        if job.is_terminal:
            return job  # Already finished
        
        job.status = JobStatus.CANCELLED
        if not job.finished_at:
            job.finished_at = datetime.utcnow()
            if job.started_at:
                job.runtime_seconds = (job.finished_at - job.started_at).total_seconds()
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info("Cancelled job", job_id=str(job_id))
        return job

    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        total_jobs = self.db.query(Job).count()
        
        # Jobs by status
        status_counts = (
            self.db.query(Job.status, func.count(Job.id))
            .group_by(Job.status)
            .all()
        )
        jobs_by_status = {status: count for status, count in status_counts}
        
        # Average runtime for successful jobs
        avg_runtime = (
            self.db.query(func.avg(Job.runtime_seconds))
            .filter(Job.status == JobStatus.SUCCESS)
            .scalar()
        )
        
        # Success rate
        success_count = jobs_by_status.get(JobStatus.SUCCESS, 0)
        success_rate = success_count / total_jobs if total_jobs > 0 else 0.0
        
        return {
            "total_jobs": total_jobs,
            "jobs_by_status": jobs_by_status,
            "avg_runtime_seconds": avg_runtime,
            "success_rate": success_rate,
        }
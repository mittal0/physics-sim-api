import uuid
from datetime import datetime

import pytest

from app.api.schemas import JobCreate, JobMetadata
from app.models.job import Job, JobStatus
from app.services.job_service import JobService


class TestJobService:
    """Test JobService functionality"""

    def test_create_single_job(self, db_session, sample_job_data):
        """Test creating a single job"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_job_data)
        
        job_ids = service.create_job(job_data)
        
        assert len(job_ids) == 1
        
        # Verify job was created in database
        job = service.get_job(job_ids[0])
        assert job is not None
        assert job.status == JobStatus.QUEUED
        assert job.container_image == sample_job_data["container_image"]
        assert job.params == sample_job_data["params"]
        assert job.created_by == sample_job_data["created_by"]

    def test_create_sweep_jobs(self, db_session, sample_sweep_data):
        """Test creating sweep jobs"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_sweep_data)
        
        job_ids = service.create_job(job_data)
        
        assert len(job_ids) == 3  # Three parameter sets
        
        # Verify all jobs were created
        for i, job_id in enumerate(job_ids):
            job = service.get_job(job_id)
            assert job is not None
            assert job.status == JobStatus.QUEUED
            assert job.params == sample_sweep_data["sweep"][i]
            assert job.parent_job_id is not None
            
        # All jobs should have the same parent_job_id
        parent_ids = [service.get_job(jid).parent_job_id for jid in job_ids]
        assert len(set(parent_ids)) == 1

    def test_build_command_from_params(self, db_session):
        """Test command building from parameters"""
        service = JobService(db_session)
        
        params = {
            "length": 1.0,
            "time_steps": 100,
            "diffusivity": 0.01,
        }
        
        command = service._build_command_from_params(params)
        
        expected = "python /sim/run_sim.py --length 1.0 --time_steps 100 --diffusivity 0.01"
        assert command == expected

    def test_get_job_not_found(self, db_session):
        """Test getting non-existent job"""
        service = JobService(db_session)
        
        non_existent_id = uuid.uuid4()
        job = service.get_job(non_existent_id)
        
        assert job is None

    def test_list_jobs_empty(self, db_session):
        """Test listing jobs when database is empty"""
        service = JobService(db_session)
        
        result = service.list_jobs()
        
        assert result.total == 0
        assert len(result.jobs) == 0
        assert result.page == 1
        assert result.size == 50
        assert not result.has_next

    def test_list_jobs_with_pagination(self, db_session, sample_job_data):
        """Test job listing with pagination"""
        service = JobService(db_session)
        
        # Create multiple jobs
        for i in range(5):
            job_data = JobCreate(**sample_job_data)
            service.create_job(job_data)
        
        # Test pagination
        result = service.list_jobs(page=1, size=3)
        
        assert result.total == 5
        assert len(result.jobs) == 3
        assert result.has_next
        
        # Second page
        result = service.list_jobs(page=2, size=3)
        assert len(result.jobs) == 2
        assert not result.has_next

    def test_list_jobs_with_filters(self, db_session, sample_job_data):
        """Test job listing with filters"""
        service = JobService(db_session)
        
        # Create jobs with different creators
        job_data_1 = JobCreate(**{**sample_job_data, "created_by": "user1"})
        job_data_2 = JobCreate(**{**sample_job_data, "created_by": "user2"})
        
        service.create_job(job_data_1)
        service.create_job(job_data_2)
        
        # Filter by creator
        result = service.list_jobs(created_by="user1")
        assert result.total == 1
        assert result.jobs[0].created_by == "user1"

    def test_update_job_status(self, db_session, sample_job_data):
        """Test updating job status"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_job_data)
        
        job_ids = service.create_job(job_data)
        job_id = job_ids[0]
        
        # Update to running
        start_time = datetime.utcnow()
        updated_job = service.update_job_status(
            job_id,
            JobStatus.RUNNING,
            started_at=start_time
        )
        
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.started_at == start_time
        
        # Update to success
        end_time = datetime.utcnow()
        updated_job = service.update_job_status(
            job_id,
            JobStatus.SUCCESS,
            finished_at=end_time,
            exit_code=0,
            result_path="/path/to/results"
        )
        
        assert updated_job.status == JobStatus.SUCCESS
        assert updated_job.finished_at == end_time
        assert updated_job.exit_code == 0
        assert updated_job.result_path == "/path/to/results"
        assert updated_job.runtime_seconds is not None

    def test_append_job_logs(self, db_session, sample_job_data):
        """Test appending logs to job"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_job_data)
        
        job_ids = service.create_job(job_data)
        job_id = job_ids[0]
        
        # Append logs
        service.append_job_logs(job_id, "Starting simulation...\n")
        service.append_job_logs(job_id, "Processing data...\n")
        
        job = service.get_job(job_id)
        assert "Starting simulation..." in job.logs
        assert "Processing data..." in job.logs

    def test_cancel_job(self, db_session, sample_job_data):
        """Test cancelling a job"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_job_data)
        
        job_ids = service.create_job(job_data)
        job_id = job_ids[0]
        
        # Cancel job
        cancelled_job = service.cancel_job(job_id)
        
        assert cancelled_job.status == JobStatus.CANCELLED
        assert cancelled_job.finished_at is not None

    def test_cancel_already_finished_job(self, db_session, sample_job_data):
        """Test cancelling an already finished job"""
        service = JobService(db_session)
        job_data = JobCreate(**sample_job_data)
        
        job_ids = service.create_job(job_data)
        job_id = job_ids[0]
        
        # First mark as success
        service.update_job_status(job_id, JobStatus.SUCCESS, finished_at=datetime.utcnow())
        
        # Try to cancel
        cancelled_job = service.cancel_job(job_id)
        
        # Should still be success, not cancelled
        assert cancelled_job.status == JobStatus.SUCCESS

    def test_get_job_stats(self, db_session, sample_job_data):
        """Test getting job statistics"""
        service = JobService(db_session)
        
        # Create jobs with different statuses
        for status in [JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.QUEUED]:
            job_data = JobCreate(**sample_job_data)
            job_ids = service.create_job(job_data)
            
            if status != JobStatus.QUEUED:
                service.update_job_status(
                    job_ids[0],
                    status,
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow(),
                    exit_code=0 if status == JobStatus.SUCCESS else 1
                )
        
        stats = service.get_job_stats()
        
        assert stats["total_jobs"] == 3
        assert stats["jobs_by_status"][JobStatus.SUCCESS] == 1
        assert stats["jobs_by_status"][JobStatus.FAILED] == 1
        assert stats["jobs_by_status"][JobStatus.QUEUED] == 1
        assert 0 <= stats["success_rate"] <= 1
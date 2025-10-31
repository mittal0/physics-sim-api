import os
import tempfile
import time
from unittest.mock import patch, Mock

import pytest

from app.models.job import JobStatus
from app.services.job_service import JobService
from app.tasks.simulation import run_simulation


@pytest.mark.integration
class TestJobWorkflow:
    """Integration tests for complete job workflow"""

    def test_complete_job_workflow(self, client, db_session, temp_artifacts_dir, sample_job_data):
        """Test complete workflow from job creation to completion"""
        
        # Mock the Celery task to run synchronously
        with patch('app.tasks.simulation.run_simulation.delay') as mock_delay:
            # Create job via API
            response = client.post("/api/v1/jobs", json=sample_job_data)
            assert response.status_code == 200
            
            job_id = response.json()["jobs"][0]
            mock_delay.assert_called_once_with(job_id)
            
            # Verify job was created in queued state
            job_response = client.get(f"/api/v1/jobs/{job_id}")
            assert job_response.status_code == 200
            job_data = job_response.json()
            assert job_data["status"] == JobStatus.QUEUED

    def test_job_execution_mock(self, db_session, temp_artifacts_dir, sample_job_data):
        """Test job execution with mocked Docker container"""
        service = JobService(db_session)
        
        # Create job
        from app.api.schemas import JobCreate
        job_data = JobCreate(**sample_job_data)
        job_ids = service.create_job(job_data)
        job_id = str(job_ids[0])
        
        # Mock Docker container execution
        mock_container = Mock()
        mock_container.id = "mock_container_123"
        mock_container.logs.return_value = [
            b"Starting simulation...\n",
            b"Processing parameters...\n",
            b"Simulation completed successfully\n"
        ]
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.get_archive.return_value = (iter([b"mock_tar_data"]), {})
        
        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        
        # Mock file extraction
        with patch('docker.from_env', return_value=mock_client), \
             patch('tarfile.open') as mock_tar, \
             patch('tempfile.NamedTemporaryFile') as mock_temp:
            
            mock_temp.return_value.__enter__.return_value.name = "/tmp/mock_archive"
            mock_tar.return_value.__enter__.return_value.extractall = Mock()
            
            # Run the simulation task
            result = run_simulation(job_id)
            
            # Verify results
            assert result["job_id"] == job_id
            assert result["status"] == JobStatus.SUCCESS
            assert result["exit_code"] == 0
            
            # Verify job was updated in database
            updated_job = service.get_job(job_ids[0])
            assert updated_job.status == JobStatus.SUCCESS
            assert updated_job.exit_code == 0
            assert "Starting simulation..." in updated_job.logs

    def test_job_execution_failure(self, db_session, temp_artifacts_dir, sample_job_data):
        """Test job execution with container failure"""
        service = JobService(db_session)
        
        # Create job
        from app.api.schemas import JobCreate
        job_data = JobCreate(**sample_job_data)
        job_ids = service.create_job(job_data)
        job_id = str(job_ids[0])
        
        # Mock Docker container failure
        mock_container = Mock()
        mock_container.id = "mock_container_456"
        mock_container.logs.return_value = [
            b"Starting simulation...\n",
            b"ERROR: Invalid parameters\n"
        ]
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.get_archive.return_value = (iter([b"mock_tar_data"]), {})
        
        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        
        with patch('docker.from_env', return_value=mock_client), \
             patch('tarfile.open') as mock_tar, \
             patch('tempfile.NamedTemporaryFile') as mock_temp:
            
            mock_temp.return_value.__enter__.return_value.name = "/tmp/mock_archive"
            
            # Run the simulation task
            result = run_simulation(job_id)
            
            # Verify failure results
            assert result["job_id"] == job_id
            assert result["status"] == JobStatus.FAILED
            assert result["exit_code"] == 1
            
            # Verify job was updated in database
            updated_job = service.get_job(job_ids[0])
            assert updated_job.status == JobStatus.FAILED
            assert updated_job.exit_code == 1

    def test_parameter_sweep_workflow(self, client, db_session, sample_sweep_data):
        """Test parameter sweep job creation and tracking"""
        
        with patch('app.tasks.simulation.run_simulation.delay') as mock_delay:
            # Create sweep jobs
            response = client.post("/api/v1/jobs", json=sample_sweep_data)
            assert response.status_code == 200
            
            data = response.json()
            job_ids = data["jobs"]
            sweep_mapping = data["sweep_mapping"]
            
            assert len(job_ids) == 3
            assert len(sweep_mapping) == 3
            assert mock_delay.call_count == 3
            
            # Verify all jobs were created with correct parameters
            for i, job_id in enumerate(job_ids):
                job_response = client.get(f"/api/v1/jobs/{job_id}")
                job_data = job_response.json()
                
                # Check that parameters match the sweep
                expected_params = sample_sweep_data["sweep"][i]
                assert job_data["params"] == expected_params
                
                # Check that all jobs have the same parent_job_id
                if i == 0:
                    parent_id = job_data["parent_job_id"]
                else:
                    assert job_data["parent_job_id"] == parent_id

    def test_job_cancellation_workflow(self, client, db_session, sample_job_data):
        """Test job cancellation workflow"""
        
        with patch('app.tasks.simulation.run_simulation.delay'):
            # Create job
            response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = response.json()["jobs"][0]
            
            # Cancel job
            cancel_response = client.delete(f"/api/v1/jobs/{job_id}")
            assert cancel_response.status_code == 200
            
            cancelled_job = cancel_response.json()
            assert cancelled_job["status"] == JobStatus.CANCELLED
            
            # Verify job status in database
            job_response = client.get(f"/api/v1/jobs/{job_id}")
            job_data = job_response.json()
            assert job_data["status"] == JobStatus.CANCELLED

    def test_log_streaming_workflow(self, client, db_session, sample_job_data):
        """Test log retrieval and streaming"""
        
        with patch('app.tasks.simulation.run_simulation.delay'):
            # Create job
            response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = response.json()["jobs"][0]
            
            # Add some logs to the job
            service = JobService(db_session)
            service.append_job_logs(job_id, "Starting simulation...\n")
            service.append_job_logs(job_id, "Processing data...\n")
            
            # Get logs via API
            logs_response = client.get(f"/api/v1/jobs/{job_id}/logs")
            assert logs_response.status_code == 200
            
            logs_data = logs_response.json()
            assert "Starting simulation..." in logs_data["logs"]
            assert "Processing data..." in logs_data["logs"]
            
            # Test log streaming
            stream_response = client.get(f"/api/v1/jobs/{job_id}/logs/stream")
            assert stream_response.status_code == 200

    def test_job_statistics_workflow(self, client, db_session, sample_job_data):
        """Test job statistics collection"""
        
        with patch('app.tasks.simulation.run_simulation.delay'):
            # Create multiple jobs
            job_ids = []
            for _ in range(3):
                response = client.post("/api/v1/jobs", json=sample_job_data)
                job_ids.extend(response.json()["jobs"])
            
            # Simulate different job outcomes
            service = JobService(db_session)
            service.update_job_status(job_ids[0], JobStatus.SUCCESS, exit_code=0)
            service.update_job_status(job_ids[1], JobStatus.FAILED, exit_code=1)
            # Leave job_ids[2] as QUEUED
            
            # Get statistics
            stats_response = client.get("/api/v1/jobs/stats")
            assert stats_response.status_code == 200
            
            stats = stats_response.json()
            assert stats["total_jobs"] == 3
            assert stats["jobs_by_status"]["success"] == 1
            assert stats["jobs_by_status"]["failed"] == 1
            assert stats["jobs_by_status"]["queued"] == 1
            assert 0 <= stats["success_rate"] <= 1

    def test_artifact_handling_workflow(self, client, db_session, temp_artifacts_dir, sample_job_data):
        """Test artifact creation and retrieval"""
        
        with patch('app.tasks.simulation.run_simulation.delay'):
            # Create job
            response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = response.json()["jobs"][0]
            
            # Simulate job completion with artifacts
            service = JobService(db_session)
            
            # Create mock artifact directory
            artifact_path = os.path.join(temp_artifacts_dir, job_id)
            os.makedirs(artifact_path, exist_ok=True)
            
            # Create mock result files
            with open(os.path.join(artifact_path, "result.csv"), "w") as f:
                f.write("time,temperature\n0.0,100.0\n0.1,90.0\n")
            
            with open(os.path.join(artifact_path, "meta.json"), "w") as f:
                f.write('{"simulation_type": "test"}')
            
            # Update job with result path
            service.update_job_status(
                job_id,
                JobStatus.SUCCESS,
                result_path=artifact_path,
                exit_code=0
            )
            
            # Try to download results
            result_response = client.get(f"/api/v1/jobs/{job_id}/result")
            assert result_response.status_code == 200
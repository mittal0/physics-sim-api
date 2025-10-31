import json
from unittest.mock import patch

import pytest

from app.models.job import JobStatus


class TestJobEndpoints:
    """Test FastAPI job endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        with patch('app.api.health.SessionLocal') as mock_db, \
             patch('redis.from_url') as mock_redis:
            
            # Mock successful database connection
            mock_db.return_value.execute.return_value = None
            mock_db.return_value.close.return_value = None
            
            # Mock successful Redis connection
            mock_redis.return_value.ping.return_value = True
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data

    def test_create_single_job(self, client, sample_job_data):
        """Test creating a single job"""
        with patch('app.tasks.simulation.run_simulation.delay') as mock_task:
            mock_task.return_value = None
            
            response = client.post("/api/v1/jobs", json=sample_job_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 1
            assert data["sweep_mapping"] is None
            mock_task.assert_called_once()

    def test_create_sweep_jobs(self, client, sample_sweep_data):
        """Test creating sweep jobs"""
        with patch('app.tasks.simulation.run_simulation.delay') as mock_task:
            mock_task.return_value = None
            
            response = client.post("/api/v1/jobs", json=sample_sweep_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 3
            assert data["sweep_mapping"] is not None
            assert len(data["sweep_mapping"]) == 3
            assert mock_task.call_count == 3

    def test_create_job_validation_error(self, client):
        """Test job creation with validation error"""
        invalid_data = {
            "params": {"length": 1.0},
            "sweep": [{"diffusivity": 0.01}]  # Both params and sweep provided
        }
        
        response = client.post("/api/v1/jobs", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_get_job(self, client, sample_job_data):
        """Test getting a job by ID"""
        # First create a job
        with patch('app.tasks.simulation.run_simulation.delay'):
            create_response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = create_response.json()["jobs"][0]
        
        # Get the job
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["status"] == JobStatus.QUEUED
        assert data["container_image"] == sample_job_data["container_image"]

    def test_get_job_not_found(self, client):
        """Test getting non-existent job"""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(f"/api/v1/jobs/{fake_id}")
        
        assert response.status_code == 404

    def test_list_jobs_empty(self, client):
        """Test listing jobs when database is empty"""
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["jobs"]) == 0

    def test_list_jobs_with_pagination(self, client, sample_job_data):
        """Test job listing with pagination"""
        # Create multiple jobs
        with patch('app.tasks.simulation.run_simulation.delay'):
            for _ in range(5):
                client.post("/api/v1/jobs", json=sample_job_data)
        
        # Test pagination
        response = client.get("/api/v1/jobs?page=1&size=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["jobs"]) == 3
        assert data["has_next"] is True

    def test_list_jobs_with_filters(self, client, sample_job_data):
        """Test job listing with filters"""
        # Create jobs with different statuses
        with patch('app.tasks.simulation.run_simulation.delay'):
            client.post("/api/v1/jobs", json=sample_job_data)
        
        # Filter by status
        response = client.get("/api/v1/jobs?status=queued")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "queued"

    def test_get_job_logs(self, client, sample_job_data):
        """Test getting job logs"""
        # Create a job
        with patch('app.tasks.simulation.run_simulation.delay'):
            create_response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = create_response.json()["jobs"][0]
        
        response = client.get(f"/api/v1/jobs/{job_id}/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "logs" in data

    def test_get_job_logs_not_found(self, client):
        """Test getting logs for non-existent job"""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(f"/api/v1/jobs/{fake_id}/logs")
        
        assert response.status_code == 404

    def test_stream_job_logs(self, client, sample_job_data):
        """Test streaming job logs"""
        # Create a job
        with patch('app.tasks.simulation.run_simulation.delay'):
            create_response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = create_response.json()["jobs"][0]
        
        response = client.get(f"/api/v1/jobs/{job_id}/logs/stream")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_cancel_job(self, client, sample_job_data):
        """Test cancelling a job"""
        # Create a job
        with patch('app.tasks.simulation.run_simulation.delay'):
            create_response = client.post("/api/v1/jobs", json=sample_job_data)
            job_id = create_response.json()["jobs"][0]
        
        response = client.delete(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.CANCELLED

    def test_cancel_job_not_found(self, client):
        """Test cancelling non-existent job"""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.delete(f"/api/v1/jobs/{fake_id}")
        
        assert response.status_code == 404

    def test_get_job_stats(self, client, sample_job_data):
        """Test getting job statistics"""
        # Create some jobs
        with patch('app.tasks.simulation.run_simulation.delay'):
            for _ in range(3):
                client.post("/api/v1/jobs", json=sample_job_data)
        
        response = client.get("/api/v1/jobs/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 3
        assert "jobs_by_status" in data
        assert "success_rate" in data

    def test_download_job_result_not_found(self, client):
        """Test downloading result for non-existent job"""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(f"/api/v1/jobs/{fake_id}/result")
        
        assert response.status_code == 404

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
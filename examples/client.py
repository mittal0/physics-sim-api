#!/usr/bin/env python3
"""
Example Python client for the Physics Simulation API

This script demonstrates how to interact with the Physics Simulation API
to submit jobs, monitor progress, and download results.
"""

import json
import time
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin


class PhysicsSimClient:
    """Client for interacting with the Physics Simulation API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the Physics Simulation API
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PhysicsSimClient/1.0'
        })
    
    def _url(self, path: str) -> str:
        """Construct full URL"""
        return urljoin(self.base_url + '/', path.lstrip('/'))
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        response = self.session.get(self._url('/health'))
        response.raise_for_status()
        return response.json()
    
    def submit_job(self, 
                   params: Dict[str, Any],
                   container_image: Optional[str] = None,
                   command: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   created_by: Optional[str] = None) -> List[str]:
        """
        Submit a single simulation job
        
        Args:
            params: Simulation parameters
            container_image: Docker image to use (optional)
            command: Command to run (optional)
            metadata: Additional metadata (optional)
            created_by: User who created the job (optional)
            
        Returns:
            List of job IDs (single item for individual jobs)
        """
        job_data = {
            "params": params,
            "metadata": metadata or {},
        }
        
        if container_image:
            job_data["container_image"] = container_image
        if command:
            job_data["command"] = command
        if created_by:
            job_data["created_by"] = created_by
        
        response = self.session.post(
            self._url('/api/v1/jobs'),
            json=job_data
        )
        response.raise_for_status()
        
        result = response.json()
        return result["jobs"]
    
    def submit_sweep(self,
                     sweep_params: List[Dict[str, Any]],
                     container_image: Optional[str] = None,
                     command: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit a parameter sweep (multiple jobs)
        
        Args:
            sweep_params: List of parameter dictionaries
            container_image: Docker image to use (optional)
            command: Command to run (optional)
            metadata: Additional metadata (optional)
            created_by: User who created the jobs (optional)
            
        Returns:
            Dictionary with job IDs and sweep mapping
        """
        job_data = {
            "sweep": sweep_params,
            "metadata": metadata or {},
        }
        
        if container_image:
            job_data["container_image"] = container_image
        if command:
            job_data["command"] = command
        if created_by:
            job_data["created_by"] = created_by
        
        response = self.session.post(
            self._url('/api/v1/jobs'),
            json=job_data
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job details by ID"""
        response = self.session.get(self._url(f'/api/v1/jobs/{job_id}'))
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self,
                  page: int = 1,
                  size: int = 50,
                  status: Optional[str] = None,
                  created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        List jobs with optional filtering
        
        Args:
            page: Page number (1-based)
            size: Page size
            status: Filter by job status
            created_by: Filter by creator
            
        Returns:
            Dictionary with jobs list and pagination info
        """
        params = {
            "page": page,
            "size": size,
        }
        
        if status:
            params["status"] = status
        if created_by:
            params["created_by"] = created_by
        
        response = self.session.get(
            self._url('/api/v1/jobs'),
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_job_logs(self, job_id: str) -> str:
        """Get job logs"""
        response = self.session.get(self._url(f'/api/v1/jobs/{job_id}/logs'))
        response.raise_for_status()
        return response.json()["logs"]
    
    def download_results(self, job_id: str, output_path: str) -> None:
        """
        Download job results
        
        Args:
            job_id: Job ID
            output_path: Local path to save results
        """
        response = self.session.get(
            self._url(f'/api/v1/jobs/{job_id}/result'),
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a job"""
        response = self.session.delete(self._url(f'/api/v1/jobs/{job_id}'))
        response.raise_for_status()
        return response.json()
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        response = self.session.get(self._url('/api/v1/jobs/stats'))
        response.raise_for_status()
        return response.json()
    
    def wait_for_job(self, job_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict[str, Any]:
        """
        Wait for a job to complete
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final job details
            
        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job["status"]
            
            if status in ["success", "failed", "cancelled"]:
                return job
            
            print(f"Job {job_id} status: {status}, waiting...")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")


def example_single_job():
    """Example: Submit and monitor a single job"""
    print("=== Single Job Example ===")
    
    client = PhysicsSimClient()
    
    # Check API health
    health = client.health_check()
    print(f"API Status: {health['status']}")
    
    # Submit a job
    job_params = {
        "length": 1.0,
        "time_steps": 100,
        "diffusivity": 0.01,
        "initial_temp": 100.0,
    }
    
    job_ids = client.submit_job(
        params=job_params,
        metadata={"project": "example", "description": "Single job test"},
        created_by="example-user"
    )
    
    job_id = job_ids[0]
    print(f"Submitted job: {job_id}")
    
    # Monitor job progress
    try:
        final_job = client.wait_for_job(job_id, timeout=120)
        print(f"Job completed with status: {final_job['status']}")
        
        if final_job['status'] == 'success':
            # Get logs
            logs = client.get_job_logs(job_id)
            print(f"Job logs:\n{logs}")
            
            # Download results
            print("Downloading results...")
            client.download_results(job_id, f"results_{job_id}.zip")
            print(f"Results saved to results_{job_id}.zip")
        else:
            print(f"Job failed with exit code: {final_job.get('exit_code')}")
            logs = client.get_job_logs(job_id)
            print(f"Error logs:\n{logs}")
            
    except TimeoutError:
        print("Job timed out, cancelling...")
        client.cancel_job(job_id)


def example_parameter_sweep():
    """Example: Submit and monitor a parameter sweep"""
    print("\n=== Parameter Sweep Example ===")
    
    client = PhysicsSimClient()
    
    # Define parameter sweep
    sweep_params = [
        {"length": 1.0, "time_steps": 50, "diffusivity": 0.01},
        {"length": 1.0, "time_steps": 100, "diffusivity": 0.01},
        {"length": 1.0, "time_steps": 200, "diffusivity": 0.01},
    ]
    
    # Submit sweep
    result = client.submit_sweep(
        sweep_params=sweep_params,
        metadata={"project": "sweep-example", "description": "Time step study"},
        created_by="example-user"
    )
    
    job_ids = result["jobs"]
    print(f"Submitted {len(job_ids)} jobs for parameter sweep")
    
    # Monitor all jobs
    completed_jobs = []
    
    for job_id in job_ids:
        print(f"Waiting for job {job_id}...")
        try:
            final_job = client.wait_for_job(job_id, timeout=60)
            completed_jobs.append(final_job)
            print(f"  Job {job_id}: {final_job['status']}")
        except TimeoutError:
            print(f"  Job {job_id}: timed out")
    
    # Summary
    successful_jobs = [j for j in completed_jobs if j["status"] == "success"]
    print(f"\nSweep completed: {len(successful_jobs)}/{len(job_ids)} jobs successful")


def example_job_listing():
    """Example: List and filter jobs"""
    print("\n=== Job Listing Example ===")
    
    client = PhysicsSimClient()
    
    # List all jobs
    all_jobs = client.list_jobs(page=1, size=10)
    print(f"Total jobs: {all_jobs['total']}")
    print(f"Current page: {all_jobs['page']}")
    
    # List successful jobs only
    successful_jobs = client.list_jobs(status="success", size=5)
    print(f"Successful jobs: {successful_jobs['total']}")
    
    # Show job details
    if successful_jobs['jobs']:
        for job in successful_jobs['jobs'][:3]:
            print(f"  Job {job['id']}: {job['status']} (runtime: {job.get('runtime_seconds', 'N/A')}s)")


def example_monitoring():
    """Example: Monitor system status"""
    print("\n=== Monitoring Example ===")
    
    client = PhysicsSimClient()
    
    # Get system health
    health = client.health_check()
    print(f"System Status: {health['status']}")
    print("Service Status:")
    for service, status in health['services'].items():
        print(f"  {service}: {status}")
    
    # Get job statistics
    stats = client.get_job_stats()
    print(f"\nJob Statistics:")
    print(f"  Total jobs: {stats['total_jobs']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Average runtime: {stats.get('avg_runtime_seconds', 'N/A')} seconds")
    
    print("Jobs by status:")
    for status, count in stats['jobs_by_status'].items():
        print(f"  {status}: {count}")


def main():
    """Run all examples"""
    try:
        # Run examples
        example_single_job()
        example_parameter_sweep()
        example_job_listing()
        example_monitoring()
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the Physics Simulation API.")
        print("Make sure the API is running at http://localhost:8000")
        print("You can start it with: make up")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
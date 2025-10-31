import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

import docker
from celery import current_task

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.job import Job, JobStatus
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.simulation.run_simulation")
def run_simulation(self, job_id: str) -> Dict[str, Any]:
    """
    Run a simulation job in a Docker container
    
    Args:
        job_id: The UUID of the job to execute
        
    Returns:
        Dict containing execution results
    """
    job_uuid = UUID(job_id)
    db = SessionLocal()
    
    try:
        # Get job from database
        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        logger.info("Starting simulation job", job_id=job_id, image=job.container_image)
        
        # Update job status to running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Create artifacts directory for this job
        # Use the host-mounted artifacts path that Docker can access
        job_artifacts_path = os.path.join("/tmp", "artifacts", str(job_id))
        os.makedirs(job_artifacts_path, exist_ok=True)
        
        # Initialize Docker client
        docker_client = docker.from_env()
        
        # Prepare container configuration
        container_config = _prepare_container_config(job, job_artifacts_path)
        
        # Run the container
        container = None
        try:
            container = docker_client.containers.run(
                **container_config,
                detach=True,
            )
            
            logger.info(
                "Container started",
                job_id=job_id,
                container_id=container.id[:12]
            )
            
            # Stream logs and monitor container
            exit_code = _monitor_container(container, job, db)
            
            # Copy results from container to host
            _extract_results(container, job_artifacts_path)
            
            # Update job status based on exit code
            if exit_code == 0:
                job.status = JobStatus.SUCCESS
                job.result_path = job_artifacts_path
                logger.info("Job completed successfully", job_id=job_id)
            else:
                job.status = JobStatus.FAILED
                logger.error("Job failed", job_id=job_id, exit_code=exit_code)
            
            job.exit_code = exit_code
            
        except docker.errors.ImageNotFound:
            logger.error("Docker image not found", job_id=job_id, image=job.container_image)
            job.status = JobStatus.FAILED
            job.exit_code = -1
            _append_job_logs(job, db, f"ERROR: Docker image '{job.container_image}' not found\n")
            
        except docker.errors.ContainerError as e:
            logger.error("Container execution failed", job_id=job_id, error=str(e))
            job.status = JobStatus.FAILED
            job.exit_code = e.exit_status
            _append_job_logs(job, db, f"ERROR: Container execution failed: {str(e)}\n")
            
        except Exception as e:
            logger.error("Unexpected error during simulation", job_id=job_id, error=str(e))
            job.status = JobStatus.FAILED
            job.exit_code = -1
            _append_job_logs(job, db, f"ERROR: Unexpected error: {str(e)}\n")
            
        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning("Failed to remove container", container_id=container.id, error=str(e))
        
        # Update final job status
        job.finished_at = datetime.utcnow()
        if job.started_at:
            job.runtime_seconds = (job.finished_at - job.started_at).total_seconds()
        
        db.commit()
        
        return {
            "job_id": job_id,
            "status": job.status,
            "exit_code": job.exit_code,
            "runtime_seconds": job.runtime_seconds,
            "result_path": job.result_path,
        }
        
    except Exception as e:
        logger.error("Critical error in simulation task", job_id=job_id, error=str(e))
        
        # Try to update job status to failed
        try:
            job = db.query(Job).filter(Job.id == job_uuid).first()
            if job:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.utcnow()
                job.exit_code = -1
                _append_job_logs(job, db, f"CRITICAL ERROR: {str(e)}\n")
                db.commit()
        except Exception:
            pass
        
        # Re-raise the exception so Celery marks the task as failed
        raise
    
    finally:
        db.close()


def _prepare_container_config(job: Job, artifacts_path: str) -> Dict[str, Any]:
    """Prepare Docker container configuration"""
    
    # Environment variables for the simulation
    environment = {
        "JOB_ID": str(job.id),
        "OUTPUT_DIR": "/tmp/output",
    }
    
    # Add job parameters as environment variables
    for key, value in job.params.items():
        env_key = f"PARAM_{key.upper()}"
        environment[env_key] = str(value)
    
    # Volume mounts
    volumes = {
        artifacts_path: {"bind": "/tmp/output", "mode": "rw"}
    }
    
    # Resource limits
    mem_limit = job.resource_limits.get("memory_limit", settings.default_memory_limit)
    cpu_limit = float(job.resource_limits.get("cpu_limit", settings.default_cpu_limit))
    
    config = {
        "image": job.container_image,
        "environment": environment,
        "volumes": volumes,
        "working_dir": "/sim",
        "mem_limit": mem_limit,
        "nano_cpus": int(cpu_limit * 1e9),  # Convert to nanocpus
        "network_disabled": True,  # Disable network for security
        "remove": False,  # We'll remove manually after extracting logs
        "stdout": True,
        "stderr": True,
    }
    
    # Add command if specified
    if job.command:
        config["command"] = job.command
    
    return config


def _monitor_container(container, job: Job, db: SessionLocal) -> int:
    """Monitor container execution and stream logs"""
    
    try:
        # Stream logs in real-time
        log_stream = container.logs(stream=True, follow=True)
        
        for chunk in log_stream:
            if chunk:
                log_line = chunk.decode('utf-8', errors='ignore')
                _append_job_logs(job, db, log_line)
                
                # Update Celery task progress (optional)
                if current_task:
                    current_task.update_state(
                        state='PROGRESS',
                        meta={'status': 'Running', 'logs': log_line}
                    )
        
        # Wait for container to finish
        result = container.wait()
        exit_code = result['StatusCode']
        
        return exit_code
        
    except Exception as e:
        logger.error("Error monitoring container", error=str(e))
        return -1


def _extract_results(container, artifacts_path: str) -> None:
    """Extract results from container to host filesystem"""
    
    try:
        # Get archive of output directory from container
        archive_stream, _ = container.get_archive("/tmp/output")
        
        # Write archive to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            for chunk in archive_stream:
                tmp_file.write(chunk)
            tmp_archive_path = tmp_file.name
        
        # Extract archive to artifacts directory
        import tarfile
        with tarfile.open(tmp_archive_path, 'r') as tar:
            tar.extractall(path=artifacts_path)
        
        # Clean up temporary file
        os.unlink(tmp_archive_path)
        
        logger.info("Results extracted successfully", artifacts_path=artifacts_path)
        
    except Exception as e:
        logger.error("Failed to extract results from container", error=str(e))


def _append_job_logs(job: Job, db: SessionLocal, logs: str) -> None:
    """Append logs to job record"""
    try:
        if job.logs:
            job.logs += logs
        else:
            job.logs = logs
        
        # Limit log size to prevent database bloat
        max_log_size = 50000  # 50KB
        if len(job.logs) > max_log_size:
            job.logs = job.logs[-max_log_size:]
        
        db.commit()
        
    except Exception as e:
        logger.error("Failed to append logs to job", error=str(e))
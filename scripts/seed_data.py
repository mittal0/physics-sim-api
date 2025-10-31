#!/usr/bin/env python3
"""
Seed script to populate the database with sample data for development and testing.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from app.core.database import SessionLocal, create_tables
from app.models.job import Job, JobStatus
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def seed_sample_jobs():
    """Create sample jobs for development"""
    db = SessionLocal()
    
    try:
        # Check if jobs already exist
        existing_jobs = db.query(Job).count()
        if existing_jobs > 0:
            logger.info(f"Database already has {existing_jobs} jobs. Skipping seed.")
            return
        
        logger.info("Creating sample jobs...")
        
        # Sample job parameters for different scenarios
        sample_jobs = [
            {
                "container_image": "sim:local",
                "command": "python /sim/run_sim.py --length 1.0 --time_steps 100 --diffusivity 0.01",
                "params": {
                    "length": 1.0,
                    "time_steps": 100,
                    "diffusivity": 0.01,
                    "initial_temp": 100.0,
                },
                "metadata": {
                    "project": "sample-heat-transfer",
                    "user": "demo-user",
                    "description": "Basic heat transfer simulation"
                },
                "created_by": "demo-user",
                "status": JobStatus.SUCCESS,
                "logs": "Starting simulation...\nProcessing parameters...\nSimulation completed successfully\n",
                "exit_code": 0,
                "runtime_seconds": 12.5,
            },
            {
                "container_image": "sim:local",
                "command": "python /sim/run_sim.py --length 2.0 --time_steps 200 --diffusivity 0.005",
                "params": {
                    "length": 2.0,
                    "time_steps": 200,
                    "diffusivity": 0.005,
                    "initial_temp": 150.0,
                },
                "metadata": {
                    "project": "extended-simulation",
                    "user": "researcher",
                    "description": "Extended simulation with finer resolution"
                },
                "created_by": "researcher",
                "status": JobStatus.RUNNING,
                "logs": "Starting simulation...\nInitializing grid...\nRunning time steps...\n",
            },
            {
                "container_image": "sim:local",
                "command": "python /sim/run_sim.py --length 0.5 --time_steps 50 --diffusivity 0.02",
                "params": {
                    "length": 0.5,
                    "time_steps": 50,
                    "diffusivity": 0.02,
                    "initial_temp": 75.0,
                },
                "metadata": {
                    "project": "quick-test",
                    "user": "demo-user",
                    "description": "Quick test simulation"
                },
                "created_by": "demo-user",
                "status": JobStatus.FAILED,
                "logs": "Starting simulation...\nERROR: Invalid parameter combination\nSimulation failed\n",
                "exit_code": 1,
                "runtime_seconds": 5.2,
            },
            {
                "container_image": "sim:local",
                "params": {
                    "length": 1.5,
                    "time_steps": 150,
                    "diffusivity": 0.015,
                    "initial_temp": 120.0,
                },
                "metadata": {
                    "project": "parameter-sweep",
                    "user": "researcher",
                    "description": "Part of parameter sweep study"
                },
                "created_by": "researcher",
                "status": JobStatus.QUEUED,
            },
        ]
        
        # Create jobs with realistic timestamps
        base_time = datetime.utcnow() - timedelta(hours=2)
        
        for i, job_data in enumerate(sample_jobs):
            created_at = base_time + timedelta(minutes=i * 15)
            
            job = Job(
                container_image=job_data["container_image"],
                command=job_data.get("command"),
                params=job_data["params"],
                metadata=job_data["metadata"],
                created_by=job_data["created_by"],
                status=job_data["status"],
                created_at=created_at,
                logs=job_data.get("logs", ""),
                exit_code=job_data.get("exit_code"),
                runtime_seconds=job_data.get("runtime_seconds"),
            )
            
            # Set timestamps based on status
            if job.status in [JobStatus.RUNNING, JobStatus.SUCCESS, JobStatus.FAILED]:
                job.started_at = created_at + timedelta(seconds=30)
            
            if job.status in [JobStatus.SUCCESS, JobStatus.FAILED]:
                job.finished_at = job.started_at + timedelta(seconds=job.runtime_seconds or 10)
            
            db.add(job)
        
        db.commit()
        
        job_count = db.query(Job).count()
        logger.info(f"Successfully created {job_count} sample jobs")
        
        # Print summary
        status_counts = {}
        for status in JobStatus:
            count = db.query(Job).filter(Job.status == status).count()
            if count > 0:
                status_counts[status] = count
        
        logger.info(f"Job status summary: {status_counts}")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    try:
        # Ensure tables exist
        create_tables()
        logger.info("Database tables verified")
        
        # Seed sample data
        seed_sample_jobs()
        
        logger.info("Database seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
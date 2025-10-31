from celery import Celery

from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging for Celery workers
setup_logging()

# Create Celery app
celery_app = Celery(
    "physics_sim",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.simulation"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.max_job_timeout,
    task_soft_time_limit=settings.max_job_timeout - 60,  # 1 minute before hard limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_compression="gzip",
    result_compression="gzip",
    task_routes={
        "app.tasks.simulation.run_simulation": {"queue": "simulation"},
    },
)

# Optional: Configure for AWS SQS if enabled
if settings.use_sqs_broker:
    celery_app.conf.update(
        broker_url=f"sqs://{settings.aws_access_key_id}:{settings.aws_secret_access_key}@",
        broker_transport_options={
            "region": settings.aws_region,
            "queue_name_prefix": "physics-sim-",
            "visibility_timeout": 3600,
            "polling_interval": 1,
        },
    )
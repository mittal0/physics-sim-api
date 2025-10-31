from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="sqlite:///./physics_sim.db",
        description="Database URL for SQLAlchemy"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and sessions"
    )
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT and other cryptographic operations"
    )
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )
    
    # Job Configuration
    default_container_image: str = Field(
        default="sim:local",
        description="Default Docker image for simulations"
    )
    artifacts_path: str = Field(
        default="./artifacts",
        description="Local path for storing job artifacts"
    )
    max_job_timeout: int = Field(
        default=3600,
        description="Maximum job timeout in seconds"
    )
    default_cpu_limit: str = Field(
        default="1.0",
        description="Default CPU limit for containers"
    )
    default_memory_limit: str = Field(
        default="512m",
        description="Default memory limit for containers"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    # AWS (Optional)
    aws_region: Optional[str] = Field(default=None, description="AWS region")
    aws_s3_bucket: Optional[str] = Field(default=None, description="AWS S3 bucket for artifacts")
    aws_sqs_queue_url: Optional[str] = Field(default=None, description="AWS SQS queue URL")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    
    # Docker
    docker_socket_path: str = Field(
        default="/var/run/docker.sock",
        description="Docker socket path"
    )

    @property
    def is_aws_enabled(self) -> bool:
        """Check if AWS configuration is available"""
        return bool(self.aws_region and self.aws_s3_bucket)

    @property
    def use_sqs_broker(self) -> bool:
        """Check if SQS should be used as Celery broker"""
        return bool(self.aws_sqs_queue_url)


settings = Settings()
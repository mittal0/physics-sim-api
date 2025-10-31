# Physics Simulation API

A production-quality REST API for managing containerized physics simulations with job orchestration, parameter sweeps, and real-time monitoring.

[![CI](https://github.com/your-org/physics-sim-api/workflows/CI/badge.svg)](https://github.com/your-org/physics-sim-api/actions)
[![codecov](https://codecov.io/gh/your-org/physics-sim-api/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/physics-sim-api)

## Features

- **REST API** for job submission and management using FastAPI
- **Containerized simulations** with Docker for isolation and reproducibility  
- **Parameter sweeps** for running multiple simulation variants
- **Job orchestration** with Celery and Redis for async processing
- **Real-time monitoring** with job logs and status tracking
- **Artifact management** with downloadable results and visualizations
- **Production ready** with proper logging, health checks, and error handling
- **Cloud deployment** scaffolding for AWS ECS/EKS
- **Physics simulation** example with 1D heat equation solver

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   REST API      │    │    Celery    │    │  Docker Engine  │
│   (FastAPI)     │───▶│   Workers    │───▶│   Simulation    │
│                 │    │              │    │   Containers    │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                     │
         ▼                       ▼                     ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │    Redis     │    │   Artifact      │
│   (Metadata)    │    │  (Broker)    │    │   Storage       │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- **Docker Desktop (v4.0+)** - [Install Docker Desktop](https://docs.docker.com/get-docker/)
- **Docker Compose (v2.0+)** - Included with Docker Desktop
- **Git** - [Install Git](https://git-scm.com/downloads)
- **curl** - For testing API endpoints

**Note:** Don't have Docker? See [DEVELOPMENT.md](./DEVELOPMENT.md) for Python-only setup.

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/mittal0/physics-sim-api.git
cd physics-sim-api

# Copy environment configuration
cp .env.example .env

# Optional: Edit configuration
nano .env
```

### 2. Build and Start All Services

```bash
# Using the Makefile (recommended)
make up

# Or using docker compose directly
docker compose up --build -d
```

This will start:
- **PostgreSQL** database on port `5432`
- **Redis** broker on port `6379`  
- **FastAPI** web service on port `8000`
- **Celery workers** (2 replicas) for job processing
- **Flower** monitoring UI on port `5555`

### 3. Initialize Database

```bash
# Run database migrations
make migrate

# Optional: Seed with sample data
make seed
```

### 4. Verify Installation

```bash
# Check overall system health
make health

# Or test individual components
curl http://localhost:8000/health
curl http://localhost:8000/docs    # API documentation
curl http://localhost:5555          # Celery monitoring
```

**Expected output:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy", 
    "celery": "healthy"
  }
}
```

## Usage Examples

### Submit a Simple Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "length": 1.0,
      "time_steps": 100,
      "diffusivity": 0.01,
      "initial_temp": 100.0
    },
    "metadata": {
      "project": "heat-transfer-demo",
      "user": "researcher"
    }
  }'
```

**Response:**
```json
{
  "jobs": ["278b41ae-8965-477d-ba28-63ef704d1bde"],
  "sweep_mapping": null
}
```

### Submit a Parameter Sweep

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "sweep": [
      {"length": 1.0, "time_steps": 100, "diffusivity": 0.01},
      {"length": 1.0, "time_steps": 200, "diffusivity": 0.005},
      {"length": 0.5, "time_steps": 100, "diffusivity": 0.02}
    ],
    "metadata": {
      "project": "parameter-study",
      "description": "Testing different diffusivity values"
    }
  }'
```

### Monitor Job Progress

```bash
# Get job details and status
JOB_ID="278b41ae-8965-477d-ba28-63ef704d1bde"
curl "http://localhost:8000/api/v1/jobs/$JOB_ID"

# View job logs
curl "http://localhost:8000/api/v1/jobs/$JOB_ID/logs"

# Stream logs in real-time (Server-Sent Events)
curl "http://localhost:8000/api/v1/jobs/$JOB_ID/logs/stream"
```

### Download Results

```bash
# Download job artifacts as ZIP
curl -o results.zip "http://localhost:8000/api/v1/jobs/$JOB_ID/result"

# Or view results directory
ls -la artifacts/$JOB_ID/
```

**Result files include:**
- `result.csv` - Time series temperature data
- `meta.json` - Simulation metadata and parameters
- `simulation_results.png` - Visualization plots
- `temperature_field.npy` - Raw simulation data
- `*.png` - Additional plots and visualizations

### List and Filter Jobs

```bash
# List all jobs with pagination
curl "http://localhost:8000/api/v1/jobs?page=1&size=10"

# Filter by status
curl "http://localhost:8000/api/v1/jobs?status=success"
curl "http://localhost:8000/api/v1/jobs?status=running"

# Filter by user
curl "http://localhost:8000/api/v1/jobs?created_by=researcher"

# Get job statistics
curl "http://localhost:8000/api/v1/jobs/stats"
```

## Development

### Available Make Commands

```bash
# Service Management
make up              # Start all services
make down            # Stop all services  
make restart         # Restart all services
make build           # Build Docker images
make rebuild         # Rebuild from scratch

# Database Operations
make migrate         # Run database migrations
make migrate-create  # Create new migration
make migrate-rollback # Rollback last migration
make seed            # Seed sample data

# Development Tools
make shell           # Open shell in web container
make shell-db        # PostgreSQL shell
make shell-redis     # Redis shell

# Testing & Quality
make test            # Run all tests
make test-unit       # Run unit tests only
make test-integration # Run integration tests
make test-cov        # Run tests with coverage
make lint            # Run code linting
make format          # Format code
make security-check  # Security analysis

# Monitoring
make logs            # View all service logs
make logs-api        # API service logs only
make logs-worker     # Worker logs only
make health          # Check service health
make status          # Show container status
make stats           # Show resource usage

# Cleanup
make clean           # Remove containers and volumes
make clean-all       # Complete cleanup including images
make clean-artifacts # Remove job artifacts

# Production
make prod-up         # Start in production mode
make prod-build      # Build production images
```

### Local Development Setup (Python)

If you prefer to develop without Docker:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Set up pre-commit hooks
pre-commit install

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/physics_sim"
export REDIS_URL="redis://localhost:6379/0"

# Start services individually
uvicorn app.main:app --reload --port 8000  # API server
celery -A app.tasks.celery_app worker --loglevel=info  # Worker
celery -A app.tasks.celery_app flower  # Monitoring
```

### Running Tests

```bash
# Run all tests with output
make test

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_job_service.py -v

# Run tests matching pattern
pytest -k "test_job_creation" -v
```

### Code Quality

```bash
# Run all quality checks
make lint

# Individual tools
black --check .          # Code formatting
isort --check-only .     # Import sorting  
flake8 app sim tests     # Style guide enforcement
mypy app                 # Type checking
bandit -r app/           # Security analysis
safety check             # Dependency vulnerability scan

# Auto-format code
make format
```

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

### Essential Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` | Celery message broker |
| `DEFAULT_CONTAINER_IMAGE` | `sim:local` | Default simulation Docker image |
| `ARTIFACTS_PATH` | `./artifacts` | Directory for storing job results |

### Advanced Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_JOB_TIMEOUT` | `3600` | Maximum job runtime (seconds) |
| `DEFAULT_CPU_LIMIT` | `1.0` | CPU limit per simulation |
| `DEFAULT_MEMORY_LIMIT` | `512m` | Memory limit per simulation |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DEBUG` | `false` | Enable debug mode |
| `API_WORKERS` | `1` | Number of API worker processes |

### Production Configuration

```bash
# Security
SECRET_KEY="your-secure-secret-key"
DEBUG=false

# Database (use managed service)
DATABASE_URL="postgresql://user:pass@prod-db:5432/physics_sim"

# Redis (use managed service)  
REDIS_URL="redis://prod-redis:6379/0"

# Scaling
API_WORKERS=4
CELERY_CONCURRENCY=4

# Monitoring
OTEL_SERVICE_NAME="physics-sim-api"
OTEL_EXPORTER_OTLP_ENDPOINT="http://your-otel-collector:4317"
```

## Physics Simulation

The included example implements a 1D heat equation solver using finite differences:

### Running Simulation Directly

```bash
# Inside the simulation container
cd sim
python run_sim.py --length 1.0 --time_steps 100 --diffusivity 0.01

# Or test with Docker
docker run --rm sim:local python run_sim.py --time_steps 10
```

### Simulation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `length` | float | `1.0` | Rod length (meters) |
| `time_steps` | int | `100` | Number of time steps |
| `spatial_steps` | int | `100` | Number of spatial grid points |
| `diffusivity` | float | `0.01` | Thermal diffusivity (m²/s) |
| `initial_temp` | float | `100.0` | Initial center temperature (°C) |
| `boundary_temp` | float | `0.0` | Boundary temperature (°C) |
| `end_time` | float | `1.0` | Simulation duration (seconds) |

### Output Files

Each completed job produces:

- **`result.csv`** - Time series temperature data
- **`meta.json`** - Simulation metadata and final parameters
- **`temperature_field.npy`** - Full 2D temperature field data
- **`time_array.npy`** - Time step values
- **`x_coordinates.npy`** - Spatial coordinates
- **`simulation_results.png`** - Temperature evolution plot
- **`temperature_profile.png`** - Final temperature profile

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs` | Submit job or parameter sweep |
| `GET` | `/api/v1/jobs/{job_id}` | Get job details and status |
| `GET` | `/api/v1/jobs` | List jobs with pagination |
| `GET` | `/api/v1/jobs/{job_id}/logs` | Get job execution logs |
| `GET` | `/api/v1/jobs/{job_id}/logs/stream` | Stream logs (Server-Sent Events) |
| `GET` | `/api/v1/jobs/{job_id}/result` | Download job results as ZIP |
| `DELETE` | `/api/v1/jobs/{job_id}` | Cancel running job |
| `GET` | `/api/v1/jobs/stats` | Get system job statistics |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Complete health check |
| `GET` | `/ready` | Readiness probe |
| `GET` | `/live` | Liveness probe |
| `GET` | `/docs` | Interactive API documentation |
| `GET` | `/redoc` | Alternative API documentation |

### Job Status Values

- **`queued`** - Job submitted and waiting for worker
- **`running`** - Job is currently executing
- **`success`** - Job completed successfully
- **`failed`** - Job failed during execution
- **`cancelled`** - Job was cancelled by user

## Deployment

### Docker Compose Production

```bash
# Production deployment with optimized settings
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or using make command
make prod-up
```

### AWS Deployment

Complete AWS deployment with ECS, RDS, and ElastiCache:

```bash
cd infra/aws

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy infrastructure
terraform apply

# Update service with new image
aws ecs update-service --cluster physics-sim --service api --force-new-deployment
```

See [AWS Deployment Guide](./infra/aws/README_AWS.md) for detailed instructions.

### Environment-Specific Recommendations

#### Development
- SQLite database for simplicity
- Local Redis instance
- Debug logging enabled
- Hot-reloading enabled

#### Staging  
- PostgreSQL database
- Managed Redis (e.g., AWS ElastiCache)
- Structured JSON logging
- Performance monitoring

#### Production
- AWS RDS (PostgreSQL)
- AWS ElastiCache (Redis)
- S3 for artifact storage
- CloudWatch logging and monitoring
- Auto-scaling enabled
- SSL/TLS termination
- Load balancer with health checks

## Monitoring & Observability

### Health Checks

```bash
# System health with service status
curl http://localhost:8000/health

# Kubernetes-style probes
curl http://localhost:8000/ready   # Readiness
curl http://localhost:8000/live    # Liveness
```

### Monitoring Tools

- **Flower** - Celery task monitoring at `http://localhost:5555`
- **API Docs** - Interactive documentation at `http://localhost:8000/docs`
- **Logs** - Structured JSON logging with configurable levels
- **Metrics** - OpenTelemetry support for metrics and tracing

### Logging

Structured JSON logging with multiple levels:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.services.job_service",
  "message": "Job completed successfully",
  "job_id": "278b41ae-8965-477d-ba28-63ef704d1bde",
  "runtime_seconds": 2.01,
  "exit_code": 0
}
```

### Metrics Integration

Enable OpenTelemetry for metrics and distributed tracing:

```bash
# Add to .env
OTEL_SERVICE_NAME="physics-sim-api"
OTEL_EXPORTER_OTLP_ENDPOINT="http://your-otel-collector:4317"
OTEL_EXPORTER_OTLP_HEADERS="api-key=your-api-key"
```

## Troubleshooting

### Common Issues

#### 1. Services won't start
```bash
# Check Docker is running
docker info

# Check port conflicts
netstat -tulpn | grep :8000
netstat -tulpn | grep :5432

# View service logs
make logs
```

#### 2. Database connection errors
```bash
# Test database connectivity
docker compose exec db psql -U postgres -d physics_sim -c "SELECT 1;"

# Reset database
make down
docker volume rm v1_postgres_data
make up
make migrate
```

#### 3. Redis connection errors
```bash
# Test Redis connectivity
docker compose exec redis redis-cli ping

# Check Redis logs
docker compose logs redis
```

#### 4. Docker permission errors (macOS/Windows)
```bash
# Ensure Docker Desktop is running and configured properly
# Check Docker Desktop -> Settings -> Resources -> File Sharing
# Make sure your project directory is shared

# Restart Docker Desktop if needed
```

#### 5. Simulation container fails
```bash
# Test simulation image directly
docker run --rm sim:local python run_sim.py --time_steps 5

# Rebuild simulation image
docker compose build sim-builder
```

#### 6. Workers not processing jobs
```bash
# Check worker status
make logs-worker

# Restart workers
docker compose restart worker

# Check Celery monitoring
open http://localhost:5555
```

### Debug Mode

Enable detailed debugging:

```bash
# Add to .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
make restart

# View detailed logs
make logs
```

### Performance Issues

```bash
# Monitor resource usage
make stats

# Check job processing rate
curl http://localhost:8000/api/v1/jobs/stats

# Scale workers if needed
docker compose up -d --scale worker=4
```

### Getting Help

1. **Check Documentation** - Review this README and [API docs](http://localhost:8000/docs)
2. **Search Issues** - Look through [GitHub Issues](https://github.com/your-org/physics-sim-api/issues)
3. **Run Diagnostics** - Use `make health` and `make logs`
4. **Create Issue** - Report bugs with logs and environment details

## Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/physics-sim-api.git`
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Set up** development environment: `make setup`

### Development Workflow

1. **Make changes** and add tests
2. **Run tests**: `make test`
3. **Check code quality**: `make lint`
4. **Format code**: `make format`
5. **Update documentation** if needed
6. **Commit**: `git commit -am 'Add amazing feature'`
7. **Push**: `git push origin feature/amazing-feature`
8. **Create** Pull Request

### Code Standards

- ✅ Write tests for all new functionality
- ✅ Follow Python type hints and docstrings
- ✅ Use structured logging with appropriate levels
- ✅ Update API documentation for changes
- ✅ Ensure Docker images build successfully
- ✅ Follow existing code style and patterns

### Testing Requirements

```bash
# All tests must pass
make test

# Code coverage should be maintained
pytest --cov=app --cov-report=term

# New features require tests
pytest tests/unit/test_new_feature.py -v
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes and version history.

---

## Project Structure

```
physics-sim-api/
├── app/                    # FastAPI application
│   ├── api/               # API routes and schemas
│   ├── core/              # Configuration and utilities
│   ├── models/            # Database models (SQLAlchemy)
│   ├── services/          # Business logic
│   └── tasks/             # Celery tasks
├── sim/                   # Physics simulation
│   ├── run_sim.py         # Heat equation solver
│   ├── Dockerfile         # Simulation container
│   └── requirements.txt   # Python dependencies
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── infra/                 # Infrastructure as Code
│   └── aws/               # AWS Terraform modules
├── scripts/               # Development utilities
├── artifacts/             # Job results storage
├── alembic/              # Database migrations
├── docker-compose.yml    # Local development
├── Dockerfile            # API service container
├── Makefile              # Development commands
├── pyproject.toml        # Python package config
├── .env.example          # Environment template
└── README.md             # This file
```

## What's Next?

- **Authentication & Authorization** - JWT-based user management
- **Advanced Monitoring** - Prometheus metrics and Grafana dashboards  
- **More Simulations** - Additional physics solvers (CFD, molecular dynamics)
- **Web UI** - Browser-based job management interface
- **Mobile API** - REST API optimizations for mobile clients
- **Kubernetes** - Native K8s deployment with operators
- **Workflow Engine** - Complex simulation pipelines
- **ML Integration** - Parameter optimization with machine learning

---

**Built with care using FastAPI, Docker, and modern Python practices.**

For questions or support, please check our [documentation](http://localhost:8000/docs) or [create an issue](https://github.com/your-org/physics-sim-api/issues).
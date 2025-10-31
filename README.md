# Physics Simulation API

A production-quality REST API for managing containerized physics simulations with job orchestration, parameter sweeps, and developer-friendly interfaces.

[![CI](https://github.com/your-org/physics-sim-api/workflows/CI/badge.svg)](https://github.com/your-org/physics-sim-api/actions)
[![codecov](https://codecov.io/gh/your-org/physics-sim-api/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/physics-sim-api)

## Features

- **REST API** for job submission and management using FastAPI
- **Containerized simulations** with Docker for isolation and reproducibility
- **Parameter sweeps** for running multiple simulation variants
- **Job orchestration** with Celery and Redis
- **Real-time monitoring** with job logs and status tracking
- **Artifact management** with downloadable results
- **Production ready** with proper logging, health checks, and error handling
- **Cloud deployment** scaffolding for AWS ECS/EKS

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

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/physics-sim-api.git
cd physics-sim-api
cp .env.example .env
```

### 2. Start Services

```bash
# Build and start all services
make up

# Or use docker-compose directly
docker-compose up --build
```

### 3. Run Database Migrations

```bash
# Run migrations
make migrate

# Or manually
docker-compose exec web alembic upgrade head
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## Usage Examples

### Submit a Single Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "container_image": "sim:local",
    "params": {
      "length": 1.0,
      "time_steps": 200,
      "diffusivity": 0.01,
      "initial_temp": 100.0
    },
    "metadata": {
      "project": "heat-transfer",
      "user": "researcher"
    }
  }'
```

Response:
```json
{
  "jobs": ["550e8400-e29b-41d4-a716-446655440000"],
  "sweep_mapping": null
}
```

### Submit a Parameter Sweep

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "container_image": "sim:local",
    "sweep": [
      {"length": 1.0, "time_steps": 200, "diffusivity": 0.01},
      {"length": 1.0, "time_steps": 400, "diffusivity": 0.005},
      {"length": 0.5, "time_steps": 200, "diffusivity": 0.02}
    ],
    "metadata": {
      "project": "parameter-study"
    }
  }'
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
```

### Get Job Logs

```bash
curl "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/logs"
```

### Download Results

```bash
curl -o results.zip "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/result"
```

### List Jobs

```bash
# List all jobs with pagination
curl "http://localhost:8000/api/v1/jobs?page=1&size=10"

# Filter by status
curl "http://localhost:8000/api/v1/jobs?status=success"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs` | Submit a job or parameter sweep |
| `GET` | `/api/v1/jobs/{job_id}` | Get job details |
| `GET` | `/api/v1/jobs` | List jobs with pagination |
| `GET` | `/api/v1/jobs/{job_id}/logs` | Get job logs |
| `GET` | `/api/v1/jobs/{job_id}/logs/stream` | Stream job logs (SSE) |
| `GET` | `/api/v1/jobs/{job_id}/result` | Download job results |
| `DELETE` | `/api/v1/jobs/{job_id}` | Cancel a job |
| `GET` | `/api/v1/jobs/stats` | Get job statistics |
| `GET` | `/health` | Health check |

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
make lint

# Format code
make format
```

### Available Make Commands

```bash
make up          # Start all services
make down        # Stop all services
make build       # Build Docker images
make test        # Run tests
make lint        # Run linting
make format      # Format code
make migrate     # Run database migrations
make logs        # View service logs
make clean       # Clean up containers and volumes
```

### Running Services Individually

```bash
# API server
uvicorn app.main:app --reload

# Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Celery flower (monitoring)
celery -A app.tasks.celery_app flower
```

## Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

### Key Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./physics_sim.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DEFAULT_CONTAINER_IMAGE` | `sim:local` | Default simulation image |
| `ARTIFACTS_PATH` | `./artifacts` | Path for storing results |
| `MAX_JOB_TIMEOUT` | `3600` | Maximum job runtime (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Sample Simulation

The included sample simulation solves the 1D heat equation using finite differences:

```bash
cd sim
python run_sim.py --length 1.0 --time_steps 100 --diffusivity 0.01
```

### Simulation Parameters

- `--length`: Rod length (meters)
- `--time_steps`: Number of time steps
- `--spatial_steps`: Number of spatial grid points
- `--diffusivity`: Thermal diffusivity (m²/s)
- `--initial_temp`: Initial center temperature (°C)
- `--boundary_temp`: Boundary temperature (°C)
- `--end_time`: Simulation duration (seconds)

### Output Files

- `result.csv`: Time series data
- `meta.json`: Simulation metadata
- `simulation_results.png`: Visualization plots
- `temperature_field.npy`: Full temperature field data

## Testing

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_job_service.py -v
```

## Deployment

### Local Deployment with Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### AWS Deployment

See [AWS Deployment Guide](./infra/aws/README_AWS.md) for detailed instructions on deploying to AWS ECS/EKS.

#### Quick AWS Setup

```bash
cd infra/aws
terraform init
terraform plan
terraform apply
```

### Environment-Specific Configuration

- **Development**: Use SQLite, local Redis, debug logging
- **Staging**: Use PostgreSQL, managed Redis, structured logging
- **Production**: Use RDS, ElastiCache, S3 for artifacts, CloudWatch logging

## Security Considerations

⚠️ **Important Security Notes**

- **Container Images**: Only run trusted simulation images. Consider using a private registry
- **Resource Limits**: Configure appropriate CPU/memory limits to prevent resource exhaustion
- **Network Isolation**: Simulation containers run with disabled networking by default
- **Input Validation**: All job parameters are validated before execution
- **Authentication**: Add authentication/authorization for production use

### Recommended Security Measures

1. Use a private Docker registry for simulation images
2. Implement job sandboxing with restricted capabilities
3. Set up proper monitoring and alerting
4. Use secrets management for sensitive configuration
5. Enable audit logging for all API operations

## Monitoring and Observability

### Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live
```

### Monitoring Tools

- **Flower**: Celery task monitoring at `http://localhost:5555`
- **API Docs**: Interactive API documentation at `http://localhost:8000/docs`
- **Logs**: Structured JSON logging with configurable levels

### Metrics

The application supports OpenTelemetry for metrics and tracing. Configure the following environment variables:

```bash
OTEL_SERVICE_NAME=physics-sim-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-otel-collector:4317
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database connectivity
   docker-compose exec db psql -U postgres -d physics_sim -c "SELECT 1;"
   ```

2. **Redis Connection Errors**
   ```bash
   # Check Redis connectivity
   docker-compose exec redis redis-cli ping
   ```

3. **Docker Permission Errors**
   ```bash
   # Ensure Docker socket permissions
   sudo chmod 666 /var/run/docker.sock
   ```

4. **Simulation Container Fails**
   ```bash
   # Test simulation image directly
   docker run --rm sim:local python run_sim.py --time_steps 5
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Getting Help

- Check the [Issues](https://github.com/your-org/physics-sim-api/issues) page
- Review [API Documentation](http://localhost:8000/docs)
- Run health checks: `curl http://localhost:8000/health`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests and linting: `make test lint`
5. Commit changes: `git commit -am 'Add feature'`
6. Push to branch: `git push origin feature-name`
7. Create a Pull Request

### Development Guidelines

- Write tests for all new functionality
- Follow Python type hints and docstring conventions
- Use structured logging with appropriate log levels
- Update documentation for API changes
- Ensure Docker images build successfully

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
│   ├── core/              # Core configuration and utilities
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   └── tasks/             # Celery tasks
├── sim/                   # Sample simulation
│   ├── run_sim.py         # Simulation script
│   ├── Dockerfile         # Simulation container
│   └── requirements.txt   # Simulation dependencies
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── infra/                 # Infrastructure as code
│   └── aws/               # AWS deployment
├── scripts/               # Helper scripts
├── docs/                  # Documentation
├── artifacts/             # Job results storage
├── alembic/              # Database migrations
├── docker-compose.yml    # Local development
├── Dockerfile            # API service container
├── Makefile              # Development commands
└── README.md             # This file
```
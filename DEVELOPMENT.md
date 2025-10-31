# Development Guide

## Docker-based Development (Recommended)

The recommended way to run this project is with Docker Compose, which handles all dependencies automatically.

### Prerequisites
- Docker Desktop with Docker Compose v2.0+

### Quick Start
```bash
make setup  # or docker compose up --build
```

## Python-Only Development (Alternative)

If you don't have Docker installed, you can run components individually for development.

### Prerequisites
- Python 3.11+
- PostgreSQL or SQLite
- Redis (optional, for full functionality)

### Setup

1. **Install Python dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

2. **Set up database:**
```bash
# For SQLite (easier setup)
export DATABASE_URL="sqlite:///./physics_sim.db"

# Or for PostgreSQL (install separately)
# export DATABASE_URL="postgresql://user:pass@localhost:5432/physics_sim"
```

3. **Run database migrations:**
```bash
alembic upgrade head
```

4. **Start the API server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Test the simulation script:**
```bash
cd sim
python run_sim.py --length 1.0 --time_steps 100 --diffusivity 0.01 --output_dir ../test_output
```

### Limitations of Python-Only Setup

- **No job queue:** Jobs run synchronously without Celery
- **No containerization:** Simulations run in the host environment
- **No Redis:** Caching and pub/sub features disabled
- **Manual dependency management:** You need to install all dependencies

### Testing Without Docker

```bash
# Install test dependencies
pip install -e .[dev]

# Run tests
pytest tests/unit/
pytest tests/unit/test_simulation.py -v
```

### API Testing

With the API server running (`uvicorn app.main:app --reload`):

```bash
# Test health endpoint
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Submit a test job (will run synchronously)
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "length": 1.0,
      "time_steps": 50,
      "diffusivity": 0.01
    },
    "metadata": {
      "project": "test"
    }
  }'
```

## Switching to Docker Later

Once you have Docker installed:

1. **Install Docker Desktop**
2. **Run the full setup:**
```bash
make setup
```

3. **All features will be available:**
   - Asynchronous job processing
   - Containerized simulations
   - Redis caching
   - Complete monitoring stack

## IDE Integration

### VS Code
Install the following extensions:
- Python
- Docker (if using Docker)
- PostgreSQL (if using PostgreSQL)

### PyCharm
- Configure Python interpreter to use the virtual environment
- Set up run configurations for FastAPI and tests

## Debugging

### Python-Only Mode
```bash
# Run with debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

### Docker Mode
```bash
# View logs
make logs
make logs-api
make logs-worker

# Shell into containers
make shell      # Web container
make shell-db   # Database
make shell-redis # Redis
```
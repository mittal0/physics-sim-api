#!/usr/bin/env python3
"""
Development setup script for running without Docker
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is 3.11+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("Error: Python 3.11+ is required")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def setup_virtualenv():
    """Set up virtual environment if it doesn't exist"""
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        if not run_command(f"{sys.executable} -m venv venv"):
            return False
    
    print("✓ Virtual environment ready")
    return True


def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    # Use the venv python
    python_cmd = "venv/bin/python" if os.name != "nt" else "venv\\Scripts\\python.exe"
    pip_cmd = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip.exe"
    
    if not run_command(f"{pip_cmd} install --upgrade pip"):
        return False
    
    if not run_command(f"{pip_cmd} install -e .[dev]"):
        return False
    
    print("✓ Dependencies installed")
    return True


def setup_database():
    """Set up SQLite database"""
    print("Setting up database...")
    
    # Create database file
    db_path = "physics_sim.db"
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"✓ Created database: {db_path}")
    
    # Set environment variable
    os.environ["DATABASE_URL"] = f"sqlite:///./{db_path}"
    
    # Run migrations
    alembic_cmd = "venv/bin/alembic" if os.name != "nt" else "venv\\Scripts\\alembic.exe"
    if not run_command(f"{alembic_cmd} upgrade head"):
        return False
    
    print("✓ Database migrations completed")
    return True


def create_env_file():
    """Create .env file for development"""
    env_content = """# Development configuration
DATABASE_URL=sqlite:///./physics_sim.db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
ARTIFACTS_PATH=./artifacts
LOG_LEVEL=INFO
DEFAULT_CONTAINER_IMAGE=sim:local
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✓ Created .env file")


def create_artifacts_dir():
    """Create artifacts directory"""
    os.makedirs("artifacts", exist_ok=True)
    print("✓ Created artifacts directory")


def test_simulation():
    """Test the simulation script"""
    print("Testing simulation script...")
    
    python_cmd = "venv/bin/python" if os.name != "nt" else "venv\\Scripts\\python.exe"
    
    # Create test output directory
    os.makedirs("test_output", exist_ok=True)
    
    cmd = f"{python_cmd} sim/run_sim.py --length 1.0 --time_steps 20 --spatial_steps 30 --end_time 0.1 --output_dir test_output"
    
    if run_command(cmd):
        print("✓ Simulation test successful")
        print("  Check test_output/ directory for results")
        return True
    else:
        print("✗ Simulation test failed")
        return False


def print_next_steps():
    """Print instructions for next steps"""
    python_cmd = "venv/bin/python" if os.name != "nt" else "venv\\Scripts\\python.exe"
    uvicorn_cmd = "venv/bin/uvicorn" if os.name != "nt" else "venv\\Scripts\\uvicorn.exe"
    
    print("\n" + "="*60)
    print("🎉 Development setup complete!")
    print("="*60)
    print("\nTo start the API server:")
    print(f"  {uvicorn_cmd} app.main:app --reload")
    print("\nThen visit:")
    print("  • API: http://localhost:8000")
    print("  • Docs: http://localhost:8000/docs")
    print("  • Health: http://localhost:8000/health")
    print("\nTo test the simulation:")
    print(f"  {python_cmd} sim/run_sim.py --help")
    print("\nTo run tests:")
    print("  pytest tests/unit/")
    print("\nFor full Docker setup (recommended):")
    print("  1. Install Docker Desktop")
    print("  2. Run: make setup")
    print("\n" + "="*60)


def main():
    """Main setup function"""
    print("Physics Simulation API - Development Setup")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Setting up virtual environment", setup_virtualenv),
        ("Installing dependencies", install_dependencies),
        ("Creating environment file", create_env_file),
        ("Creating directories", create_artifacts_dir),
        ("Setting up database", setup_database),
        ("Testing simulation", test_simulation),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"✗ Failed: {step_name}")
            print("\nSetup failed. Please check the errors above.")
            sys.exit(1)
    
    print_next_steps()


if __name__ == "__main__":
    main()
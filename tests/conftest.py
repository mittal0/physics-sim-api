import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing"""
    db_fd, db_path = tempfile.mkstemp()
    test_database_url = f"sqlite:///{db_path}"
    
    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def db_session(temp_db):
    """Get a database session for testing"""
    session = temp_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Create a test client with database dependency override"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def temp_artifacts_dir():
    """Create a temporary artifacts directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Override the artifacts path for testing
        original_path = settings.artifacts_path
        settings.artifacts_path = temp_dir
        
        yield temp_dir
        
        # Restore original path
        settings.artifacts_path = original_path


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "container_image": "sim:local",
        "command": "python /sim/run_sim.py --time_steps 10 --spatial_steps 10",
        "params": {
            "length": 1.0,
            "time_steps": 10,
            "spatial_steps": 10,
            "diffusivity": 0.01,
        },
        "metadata": {
            "project": "test-project",
            "user": "test-user",
        },
        "created_by": "test-user",
    }


@pytest.fixture
def sample_sweep_data():
    """Sample sweep job data for testing"""
    return {
        "container_image": "sim:local",
        "sweep": [
            {"length": 1.0, "time_steps": 10, "diffusivity": 0.01},
            {"length": 1.0, "time_steps": 20, "diffusivity": 0.005},
            {"length": 0.5, "time_steps": 10, "diffusivity": 0.02},
        ],
        "metadata": {
            "project": "test-sweep",
            "user": "test-user",
        },
        "created_by": "test-user",
    }
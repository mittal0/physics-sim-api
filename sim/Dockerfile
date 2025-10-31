# Dockerfile for Physics Simulation Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for scientific computing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create simulation user
RUN useradd --create-home --shell /bin/bash sim

# Set work directory
WORKDIR /sim

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulation scripts
COPY run_sim.py .
COPY __init__.py .

# Create output directory
RUN mkdir -p /tmp/output && chown -R sim:sim /tmp/output

# Switch to sim user
USER sim

# Make simulation script executable
RUN chmod +x run_sim.py

# Health check - verify the simulation can run with minimal parameters
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python run_sim.py --time_steps 10 --spatial_steps 10 --end_time 0.01 --output_dir /tmp/health_check || exit 1

# Default command
CMD ["python", "run_sim.py"]
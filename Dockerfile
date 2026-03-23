# DevAssist Container Image
# For deployment on OpenShift/Kubernetes

FROM registry.access.redhat.com/ubi9/python-311:latest

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir psycopg2-binary

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user directory for data
RUN mkdir -p /app/data && chmod 777 /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DEVASSIST_STORAGE=postgres

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

# Run the daemon worker
CMD ["python", "scripts/daemon_worker.py"]

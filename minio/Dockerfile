FROM python:3.9-slim

WORKDIR /app

# Install MinIO Python client
RUN pip install --no-cache-dir minio==7.2.0

# Copy initialization script
COPY init_minio.py .

# Run initialization
CMD ["python", "init_minio.py"]

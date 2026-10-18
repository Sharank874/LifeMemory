# LifeMemory AI Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy production requirements first for better caching
COPY requirements.prod.txt .

# Install Python dependencies (production only - no ML/eval tools)
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check (uses /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)"

# Run application (uses centralized config from .env)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


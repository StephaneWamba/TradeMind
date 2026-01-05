# Multi-stage Dockerfile for backend
# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files from backend directory
COPY backend/pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Stage 2: Runtime
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code from backend directory
COPY backend/ .

# Copy startup script from root
COPY start.sh /app/start.sh

# Set PYTHONPATH so app module can be found
ENV PYTHONPATH=/app/src

# Make startup script executable
RUN chmod +x /app/start.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["/app/start.sh"]


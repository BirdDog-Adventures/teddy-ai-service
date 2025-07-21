FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy Snowflake private key
COPY keys/rsa_key.p8 /app/keys/rsa_key.p8

# Create non-root user
RUN useradd -m -u 1000 teddy && chown -R teddy:teddy /app
USER teddy

# Expose port
EXPOSE 8000

# Health check disabled - ALB health check is sufficient
# HEALTHCHECK --interval=60s --timeout=30s --start-period=300s --retries=5 \
#     CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

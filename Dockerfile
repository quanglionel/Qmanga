FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for curl_cffi and building packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libcurl4 \
    libnss3 \
    libnspr4 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create data directory for persistent storage
RUN mkdir -p /app/data

WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run with production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

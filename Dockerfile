FROM python:3.11

WORKDIR /app

# Install system dependencies + Node.js for cloudscraper
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libnss3 \
    curl \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
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

# Run with production server, using PORT env var if available (required for Railway)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

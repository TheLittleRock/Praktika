FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (build-essential and libmupdf headers if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PRAKTIKA_DATA_DIR=/app/data

# Ensure data directory exists
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


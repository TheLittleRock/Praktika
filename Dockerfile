FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (curl and TrueType fonts for Czech/Slovak diacritics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy application source and documentation
COPY app/ ./app/
COPY CHANGELOG.md .
COPY docs/ ./docs/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PRAKTIKA_DATA_DIR=/app/data

# Ensure data directory exists
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


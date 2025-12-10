FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for llama-cpp-python and weasyprint
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app

# Create necessary directories
RUN mkdir -p /app/ota /app/reports /app/models /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

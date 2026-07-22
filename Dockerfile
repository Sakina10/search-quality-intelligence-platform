# ==========================================
# Stage 1: Base image with system dependencies
# ==========================================
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system utilities and PostgreSQL dev libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python package installer updates
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ==========================================
# Stage 2: Development / Test Environment
# ==========================================
FROM base AS dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY . .

# Default command for development (override in compose or make)
CMD ["bash"]

# ==========================================
# Stage 3: Model Serving API (Production)
# ==========================================
FROM base AS serving

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files needed for serving
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY models/ /app/models/

ENV PYTHONPATH=.

EXPOSE 8000
CMD ["uvicorn", "src.serving.api:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# Stage 4: Dashboard Visualization (Production)
# ==========================================
FROM base AS dashboard

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files needed for dashboard
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY models/ /app/models/

ENV PYTHONPATH=.

EXPOSE 8501
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]


# Use Ubuntu 24.04 as the base image
FROM ubuntu:24.04

# Avoid interactive prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive

# Install system and build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libsqlite3-dev \
    libreadline-dev \
    libffi-dev \
    libbz2-dev \
    liblzma-dev \
    curl \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Download and compile Python 3.14.6 from source
RUN curl -O https://www.python.org/ftp/python/3.14.6/Python-3.14.6.tgz \
    && tar -xf Python-3.14.6.tgz \
    && cd Python-3.14.6 \
    && ./configure --with-ensurepip=install \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf Python-3.14.6 Python-3.14.6.tgz

# Set up the work directory
WORKDIR /app

# Copy application files
COPY . .

# Create a single virtual environment (.venv) with Python 3.14 and install dependencies
RUN python3 -m venv .venv && \
    ./.venv/bin/pip install --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt

# Expose the Cloud Run port (default is 8080)
EXPOSE 8080
ENV PORT=8080

# Run the FastAPI app via uvicorn on port 8080
CMD ["./.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# Use CUDA runtime that matches your Vast.ai instance (this example uses CUDA 11.8)
FROM nvidia/cuda:12.0.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install OS packages
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    ffmpeg \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install PyTorch for CUDA 11.8 (change cu118 to match your base image's CUDA if different)
# NOTE: Remove torch from requirements.txt to avoid conflicts, or keep both but be mindful of versions.
RUN pip3 install --no-cache-dir --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio

# Install the rest of Python dependencies from requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Default entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

FROM python:3.11-slim

# Install ONLY what is needed for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3-renderpm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (including server/dist)
COPY . .

# Set permissions for logs (HF runs as non-root user 1000)
RUN mkdir -p /app/logs && chmod 777 /app/logs

# HF Spaces mandatory port
EXPOSE 7860

# Correct entry point pointing to the 'server' folder
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
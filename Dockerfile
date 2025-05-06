FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files into container
COPY . /app

# Initialize and update git submodules
RUN git submodule update --init --recursive

# Install Python dependencies
RUN pip install --no-cache-dir fastapi[standard]==0.113.0 \
    uvicorn[standard]==0.27.1 \
    python-multipart==0.0.9

# Expose port
EXPOSE 8000

# Start the app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


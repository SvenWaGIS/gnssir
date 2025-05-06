FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone your full repo with submodules
WORKDIR /app
RUN git clone --recurse-submodules https://github.com/SvenWaGIS/gnssir.git . 

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Expose port
EXPOSE 8000

# Start the app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]



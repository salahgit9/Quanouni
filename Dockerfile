
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for some python packages or tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any updated dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# CRITICAL: Change working directory to backend/ as per lessons learned
WORKDIR /app/backend

# Expose the port that Uvicorn will run on
EXPOSE 8000

# CRITICAL: Fix ModuleNotFoundError by explicitly setting PYTHONPATH
ENV PYTHONPATH=/app/backend

# Define environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Run the command to start Uvicorn (path is now relative to /app/backend, so 'app.main')
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

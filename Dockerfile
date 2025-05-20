# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent caching issues and ensure output is logged immediately
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Optional: Set default timezone for consistency if needed
# ENV TZ=Etc/UTC
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set work directory
WORKDIR /app

# Install system dependencies if needed by any Python package (unlikely for this set)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code into the container
# Ensure source files are in 'app' and context files are in 'context_data' at the build context root
COPY ./app /app/app
COPY ./context_data /app/context_data

# Expose the port the app runs on (must match the CMD port)
EXPOSE 8000

# Command to run the application using Uvicorn
# Use --host 0.0.0.0 to make it accessible from outside the container
# --port 8000 matches the EXPOSE directive
# --log-level matches the level set in config.py by default (INFO) but can be overridden
# Add --workers 2 (or more) for production deployments behind a load balancer/proxy (requires gunicorn usually)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
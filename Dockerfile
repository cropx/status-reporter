FROM python:3.11-slim

# Install kubectl
RUN apt-get update && \
    apt-get install -y curl && \
    curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pika==1.3.2

# Copy the status reporter script
COPY status_reporter.py /app/status_reporter.py

WORKDIR /app

# Make script executable
RUN chmod +x status_reporter.py

# Run the reporter
CMD ["python3", "/app/status_reporter.py"]

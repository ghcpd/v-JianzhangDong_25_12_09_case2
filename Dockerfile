FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    zip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY inputs.py /app/
COPY inputs_backup.py /app/
COPY requirements.txt /app/
COPY auto_test.py /app/
COPY run_test.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p /app/logs

# Create config directory for safe file operations
RUN mkdir -p /app/config

# Set environment variables for secure operation
ENV FLASK_ENV=production
ENV PAYMENT_TOKEN=default_token
ENV MAIL_SERVER_KEY=default_key
ENV INTERNAL_AUTH=default_auth
ENV DB_FILE=/app/appdata.db

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command - run tests
CMD ["python", "auto_test.py"]

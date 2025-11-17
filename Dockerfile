# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    gettext \
    curl \
    netcat-openbsd \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy docker scripts first (for better caching)
COPY docker/entrypoint.sh /docker-entrypoint.sh
COPY docker/healthcheck.sh /docker-healthcheck.sh
RUN chmod +x /docker-entrypoint.sh /docker-healthcheck.sh

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs

# Create non-root user for security
RUN groupadd -r django && useradd -r -g django django

# Set proper permissions (before switching user)
RUN chown -R django:django /app \
    && chmod +x /docker-entrypoint.sh /docker-healthcheck.sh

# Switch to non-root user for security
# Note: Some operations may require root (like binding to port < 1024)
# For port 8000, non-root user is fine
USER django

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Health check (using the healthcheck script)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /docker-healthcheck.sh || exit 1

# Default command (will be executed by entrypoint.sh)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "BudgetsSystem.wsgi:application"]

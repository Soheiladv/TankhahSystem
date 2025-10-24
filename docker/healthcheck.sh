#!/bin/bash
# Health check script for the Django application

# Check if the application is responding
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "Application is healthy"
    exit 0
else
    echo "Application is not responding"
    exit 1
fi

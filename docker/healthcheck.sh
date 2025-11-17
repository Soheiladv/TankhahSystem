#!/bin/bash
# Health check script for the Django application

# Try to check if the application is responding
# First try the /health/ endpoint, if that fails, try the root
if curl -f -s http://localhost:8000/health/ > /dev/null 2>&1; then
    exit 0
elif curl -f -s http://localhost:8000/ > /dev/null 2>&1; then
    exit 0
else
    # If curl fails, try to check if the process is running
    if pgrep -f "gunicorn" > /dev/null; then
        exit 0
    else
        exit 1
    fi
fi

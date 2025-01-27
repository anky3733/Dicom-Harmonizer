#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Print debug information
echo "Starting Flask app with Gunicorn..."

# Gunicorn configuration
WORKERS=${WORKERS:-8}  # Default to 8 workers, override with WORKERS environment variable
BIND=${BIND:-0.0.0.0:5000}  # Default bind address, override with BIND environment variable
TIMEOUT=${TIMEOUT:-120}  # Default timeout of 120 seconds, override with TIMEOUT environment variable

# Start Gunicorn for the Flask app
exec gunicorn --workers=$WORKERS app:app --bind $BIND --timeout $TIMEOUT

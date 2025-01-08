#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate

if [ "$DJANGO_ENV" = "development" ]; then
    echo "Starting Development Server..."
    python manage.py runserver 0.0.0.0:${PORT:-8000}
else
    echo "Starting Production Server..."
    gunicorn spam_detector.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers=${GUNICORN_WORKERS:-3} \
        --worker-class=gthread \
        --threads=${GUNICORN_THREADS:-3} \
        --timeout=${GUNICORN_TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        --log-level=${LOG_LEVEL:-info} \
        --max-requests=${MAX_REQUESTS:-1000} \
        --max-requests-jitter=${MAX_REQUESTS_JITTER:-50}
fi 
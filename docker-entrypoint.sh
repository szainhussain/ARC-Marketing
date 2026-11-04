#!/bin/sh
set -e

echo "Running database migrations..."
flask db upgrade
flask seed-plans

# With arguments (e.g. the compose "worker" service: `flask --app wsgi.py worker`)
# run that command; otherwise serve the API.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec gunicorn --bind 0.0.0.0:8000 --workers 2 --graceful-timeout 30 wsgi:app

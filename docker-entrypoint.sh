#!/bin/sh
set -e

echo "Running database migrations..."
flask db upgrade

exec gunicorn --bind 0.0.0.0:8000 --workers 2 wsgi:app

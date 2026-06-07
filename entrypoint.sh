#!/bin/sh
set -e

echo "[entrypoint] migrate"
python manage.py migrate --noinput

echo "[entrypoint] collectstatic"
python manage.py collectstatic --noinput

echo "[entrypoint] gunicorn"
exec gunicorn expertise.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
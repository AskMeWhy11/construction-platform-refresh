#!/bin/sh
set -e

echo "[entrypoint] migrate"
python manage.py migrate --noinput

echo "[entrypoint] collectstatic"
python manage.py collectstatic --noinput

# loaddata справочников только при первом старте (флаг-файл в volume)
if [ ! -f /app/data/.seeded ]; then
    echo "[entrypoint] loaddata demo fixtures"
    python manage.py loaddata calc/fixtures/demo.json || true
    touch /app/data/.seeded
fi

echo "[entrypoint] gunicorn"
exec gunicorn expertise.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
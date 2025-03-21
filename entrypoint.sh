#!/bin/sh

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do sleep 1; done

echo "Apply migrations"
python manage.py migrate

echo "Starting Django..."
exec "$@"

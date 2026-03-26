#!/bin/sh

set -e

echo "Warte auf PostgreSQL auf $DB_HOST:$DB_PORT..."

# -q für "quiet" (keine Ausgabe außer Fehlern)
# Die Schleife läuft, solange pg_isready *nicht* erfolgreich ist (Exit-Code != 0)
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  echo "PostgreSQL ist nicht erreichbar - schlafe 1 Sekunde"
  sleep 1
done

echo "PostgreSQL ist bereit - fahre fort..."

# Fix potential migration inconsistency (admin applied before users)
python manage.py shell << 'PYEOF'
from django.db import connection
from datetime import datetime, timezone
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('django_migrations')")
        if cursor.fetchone()[0]:
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='admin'")
            admin_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='users'")
            users_count = cursor.fetchone()[0]
            if admin_count > 0 and users_count == 0:
                cursor.execute("SELECT to_regclass('users_customuser')")
                if cursor.fetchone()[0]:
                    cursor.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES ('users', '0001_initial', %s)",
                        [datetime.now(timezone.utc)]
                    )
                    print("Fixed: recorded missing users migration (table already existed).")
except Exception as e:
    print(f"Migration pre-check skipped: {e}")
PYEOF

# Deine originalen Befehle (ohne wait_for_db)
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# Create a superuser using environment variables
# (Dein Superuser-Erstellungs-Code bleibt gleich)
python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'adminpassword')

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser '{username}'...")
    # Korrekter Aufruf: username hier übergeben
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created.")
else:
    print(f"Superuser '{username}' already exists.")
EOF

python manage.py rqworker default &

exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --reload

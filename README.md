# Videoflix Backend

Django REST Framework Backend für die Videoflix-Plattform. Unterstützt Video-Upload, HLS-Streaming, JWT-Authentifizierung via HttpOnly Cookies und Hintergrundverarbeitung mit FFMPEG.

## Technologie-Stack

| Technologie | Zweck |
|---|---|
| Django 5.2 + DRF | REST API |
| PostgreSQL | Hauptdatenbank |
| Redis | Cache + RQ Job Queue |
| Django-RQ | Hintergrund-Tasks (FFMPEG) |
| FFMPEG | Video → HLS Konvertierung |
| SimpleJWT | JWT-Authentifizierung |
| WhiteNoise | Static Files |
| Gunicorn | WSGI Server |

## Schnellstart mit Docker

### 1. `.env` Datei anlegen

```bash
cp .env.example .env
```

`.env` anpassen — mindestens diese Felder ausfüllen:

```env
SECRET_KEY=dein-geheimer-schluessel
DB_NAME=videoflix
DB_USER=videoflix_user
DB_PASSWORD=sicheres-passwort
DB_HOST=db
REDIS_URL=redis://redis:6379

EMAIL_HOST_USER=deine@email.com
EMAIL_HOST_PASSWORD=dein-app-passwort
FRONTEND_URL=http://127.0.0.1:5500

DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=adminpassword
```

### 2. Docker starten

```bash
docker-compose up --build
```

Der Container führt beim Start automatisch aus:
- `collectstatic`
- `makemigrations` + `migrate`
- Superuser erstellen (aus `.env`)
- RQ Worker starten (Hintergrund)
- Gunicorn starten auf Port 8000

### 3. Admin-Panel

```
http://localhost:8000/admin/
```

Dort können Videos hochgeladen werden. Nach dem Upload startet automatisch die FFMPEG-Konvertierung im Hintergrund.

---

## API Endpoints

### Authentifizierung

| Methode | URL | Beschreibung | Auth |
|---|---|---|---|
| POST | `/api/register/` | Registrierung | Nein |
| GET | `/api/activate/<uid>/<token>/` | Account aktivieren | Nein |
| POST | `/api/login/` | Login (setzt Cookies) | Nein |
| POST | `/api/logout/` | Logout | Cookie |
| POST | `/api/token/refresh/` | Token erneuern | Cookie |
| POST | `/api/password_reset/` | Reset-Mail senden | Nein |
| POST | `/api/password_confirm/<uid>/<token>/` | Neues Passwort | Nein |

### Videos

| Methode | URL | Beschreibung | Auth |
|---|---|---|---|
| GET | `/api/video/` | Alle Videos | JWT |
| GET | `/api/video/<id>/<res>/index.m3u8` | HLS Playlist | JWT |
| GET | `/api/video/<id>/<res>/<segment>/` | HLS Segment | JWT |

---

## Authentifizierung (HttpOnly Cookies)

Das Backend nutzt JWT-Token die als **HttpOnly Cookies** gesetzt werden — kein LocalStorage, kein Bearer-Header.

- `access_token` Cookie: 30 Minuten gültig
- `refresh_token` Cookie: 7 Tage gültig, wird bei Refresh rotiert und blacklistet

---

## Video-Processing Pipeline

```
Admin Upload im Django Admin
        ↓
Django Signal (post_save)
        ↓
Django-RQ enqueue → Redis Queue
        ↓
RQ Worker (Hintergrundprozess)
        ↓
FFMPEG → 480p / 720p / 1080p HLS (.m3u8 + .ts Segmente)
FFMPEG → Thumbnail (Frame bei 2s)
        ↓
Video.processing_status = 'done'
```

### HLS Dateistruktur

```
media/
├── uploads/videos/     ← Original-Upload
├── thumbnails/         ← Auto-generiert durch FFMPEG
└── hls/
    └── {video_id}/
        ├── 480p/  index.m3u8 + 000.ts, 001.ts, ...
        ├── 720p/  index.m3u8 + *.ts
        └── 1080p/ index.m3u8 + *.ts
```

---

## Lokale Entwicklung (ohne Docker)

```bash
# Virtuelle Umgebung
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Abhängigkeiten
pip install -r requirements.txt

# .env laden (oder Umgebungsvariablen setzen)
cp .env.example .env
# DB_HOST=localhost setzen

# Migrationen
python manage.py migrate

# Server starten
python manage.py runserver

# RQ Worker (separates Terminal)
python manage.py rqworker default
```

### E-Mail lokal testen

In `.env` setzen:
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
→ E-Mails erscheinen dann im Terminal statt versendet zu werden.

---

## Projektstruktur

```
Videoflix/
├── core/                   ← Django-Projekt
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/                  ← Auth-App
│   ├── models.py           ← CustomUser (email-basiert)
│   ├── views.py            ← Auth Views
│   ├── utils.py            ← E-Mail, Token, Cookie Hilfsfunktionen
│   ├── serializers.py
│   ├── authentication.py   ← CookieJWTAuthentication
│   └── urls.py
├── videos/                 ← Video-App
│   ├── models.py           ← Video Model
│   ├── views.py            ← HLS Serving Views
│   ├── tasks.py            ← RQ Background Tasks
│   ├── signals.py          ← post_save → enqueue
│   ├── utils.py            ← FFMPEG Hilfsfunktionen
│   └── urls.py
├── templates/
│   └── emails/             ← HTML E-Mail Templates
├── manage.py
├── requirements.txt
├── .env.example
├── backend.Dockerfile
├── backend.entrypoint.sh
└── docker-compose.yml
```

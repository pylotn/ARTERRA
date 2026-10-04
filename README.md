# ARTERRA

Django gallery and artwork shop.

## Local setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Add categories and artworks in `/admin/`.
For local development the email backend writes messages to the console.

## Before deployment

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` in the
hosting environment. Serve the site over HTTPS and run `python manage.py
collectstatic`. Uploaded artwork is stored under `media/`; configure persistent
media storage or an object-storage service for production.

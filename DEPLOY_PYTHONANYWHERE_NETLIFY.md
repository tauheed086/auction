# Free Deployment: PythonAnywhere + Netlify

This setup keeps your current Django SQLite DB and uploaded media files online for free:
- Backend: PythonAnywhere free web app
- Frontend: Netlify Free static site

## 0. What free-tier limits you should expect

- PythonAnywhere free account:
  - 1 web app, 1 web worker
  - 512 MiB storage
  - `yourusername.pythonanywhere.com` domain only
- Netlify free account:
  - Free plan with monthly usage limits

## 1. Prepare and push code from your machine

Run from repo root (`D:\Django project\auction`):

```powershell
git add .
git add -f auction_backend/db.sqlite3
git add -f auction_backend/media
git commit -m "Deploy to PythonAnywhere + Netlify"
git push
```

The forced add includes your current data snapshot (database + images).

## 2. Deploy frontend on Netlify (get domain first)

1. Login to Netlify.
2. Import repo and choose:
   - Base directory: `auction-frontend`
   - Build command: `npm ci && npm run build`
   - Publish directory: `dist`
3. Keep `VITE_API_BASE_URL` empty for now and deploy once.
4. Copy your Netlify site URL (example: `https://your-site.netlify.app`).

SPA routing is already configured via:
- `netlify.toml`

## 3. Deploy backend on PythonAnywhere

1. Create a free PythonAnywhere account and open a Bash console.
2. Clone your repo:

```bash
cd ~
git clone https://github.com/<your-user>/<your-repo>.git auction
cd ~/auction/auction_backend
```

3. Create venv and install dependencies:

```bash
mkvirtualenv --python=/usr/bin/python3.12 auction-env
workon auction-env
pip install -r requirements.txt
```

4. Set environment variables in the PythonAnywhere WSGI file.

Open **Web** tab -> your web app -> **WSGI configuration file**.
At the top, add:

```python
import os

os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_SECRET_KEY"] = "replace-with-long-random-secret"
os.environ["DJANGO_ALLOWED_HOSTS"] = "<your-username>.pythonanywhere.com"
os.environ["DJANGO_TIME_ZONE"] = "Asia/Kolkata"
os.environ["DJANGO_STATIC_ROOT"] = "/home/<your-username>/auction/auction_backend/staticfiles"
os.environ["DJANGO_MEDIA_ROOT"] = "/home/<your-username>/auction/auction_backend/media"
os.environ["DATABASE_URL"] = "sqlite:////home/<your-username>/auction/auction_backend/db.sqlite3"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://<your-netlify-site>.netlify.app"
os.environ["CSRF_TRUSTED_ORIGINS"] = "https://<your-netlify-site>.netlify.app"
os.environ["AUCTION_RESET_PIN"] = "set-a-strong-pin"
os.environ["SERVE_MEDIA_FILES"] = "True"
os.environ["DJANGO_SECURE_SSL_REDIRECT"] = "True"
os.environ["DJANGO_SECURE_HSTS_SECONDS"] = "31536000"
os.environ["DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS"] = "True"
os.environ["DJANGO_SECURE_HSTS_PRELOAD"] = "True"
```

5. In the same WSGI file, ensure project path is added and Django app is loaded:

```python
import sys
path = '/home/<your-username>/auction/auction_backend'
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auction_backend.settings')
```

6. Back in Bash console:

```bash
cd ~/auction/auction_backend
workon auction-env
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

7. In **Web** tab:
  - Set **Source code** to: `/home/<your-username>/auction/auction_backend`
  - Set **Working directory** to: `/home/<your-username>/auction/auction_backend`
  - Under **Static files**, add:
    - URL `/static/` -> `/home/<your-username>/auction/auction_backend/staticfiles`
    - URL `/media/` -> `/home/<your-username>/auction/auction_backend/media`
  - Click **Reload**.

Your backend URL will be:
`https://<your-username>.pythonanywhere.com`

## 4. Point Netlify frontend to backend

In Netlify Site settings -> Environment variables:
- `VITE_API_BASE_URL=https://<your-username>.pythonanywhere.com`

Trigger a redeploy.

## 5. Final checks

1. Open frontend URL and confirm players list loads.
2. Open `/admin-board` and test login.
3. Add/edit player image and verify it loads after refresh.
4. Sell/skip players and verify changes persist.

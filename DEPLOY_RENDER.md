# Render Deployment (Keep Current DB + Media)

This project is configured to deploy on Render with:
- Backend: `auction_backend` Django web service
- Frontend: `auction-frontend` static web service
- Persistent disk for SQLite and uploaded images

## 1. Commit your current app state (including DB/media snapshot if needed)

If you want production to start with your exact current data, include these files once:

```bash
git add -f auction_backend/db.sqlite3 auction_backend/media
git add .
git commit -m "Prepare Render deployment with current data snapshot"
git push
```

If you do not include them, deployment still works but starts from empty DB/media.

## 2. Create services in Render from `render.yaml`

1. Push your repo to GitHub/GitLab.
2. In Render dashboard, choose `New` -> `Blueprint`.
3. Select your repo root (contains `render.yaml`).
4. Render creates:
- `auction-backend` (Python web service + disk at `/var/data`)
- `auction-frontend` (Static site)

## 3. Update environment values

In Render service settings, set:
- Backend `DJANGO_ALLOWED_HOSTS` to your real backend domain(s), comma-separated.
- Backend `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to your real frontend domain(s).
- Backend `AUCTION_RESET_PIN` to a strong secret.
- Frontend `VITE_API_BASE_URL` to your backend URL.

## 4. Verify first deploy seeding behavior

On first backend deploy:
- `start.sh` seeds `/var/data/db.sqlite3` from repo `db.sqlite3` if missing.
- `start.sh` seeds `/var/data/media` from repo `media/` if target folder is empty.

Then it runs:
- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`
- `gunicorn auction_backend.wsgi:application`

Subsequent deploys keep persisted DB/media from disk.

## 5. Post-deploy checks

1. Open frontend URL and verify player list.
2. Open admin board and test login.
3. Confirm player images load.
4. Sell/skip one player and refresh to confirm DB persistence.

#!/usr/bin/env bash
set -o errexit
set -o nounset

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# Seed persistent sqlite DB from repo copy on first deploy only.
if [[ "${DATABASE_URL:-}" =~ ^sqlite:/// ]]; then
  DB_PATH="${DATABASE_URL#sqlite:///}"
elif [[ -n "${SQLITE_DB_PATH:-}" ]]; then
  DB_PATH="${SQLITE_DB_PATH}"
else
  DB_PATH=""
fi

if [[ -n "${DB_PATH}" ]]; then
  mkdir -p "$(dirname "${DB_PATH}")"
  if [[ ! -f "${DB_PATH}" && -f "${APP_DIR}/db.sqlite3" ]]; then
    echo "Seeding sqlite database to persistent disk: ${DB_PATH}"
    cp "${APP_DIR}/db.sqlite3" "${DB_PATH}"
  fi
fi

MEDIA_TARGET="${DJANGO_MEDIA_ROOT:-}"
if [[ -n "${MEDIA_TARGET}" ]]; then
  mkdir -p "${MEDIA_TARGET}"
  if [[ -d "${APP_DIR}/media" ]] && [[ -z "$(ls -A "${MEDIA_TARGET}" 2>/dev/null)" ]]; then
    echo "Seeding media files to persistent disk: ${MEDIA_TARGET}"
    cp -a "${APP_DIR}/media/." "${MEDIA_TARGET}/"
  fi
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn auction_backend.wsgi:application --log-file -

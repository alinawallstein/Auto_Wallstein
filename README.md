# Auto Wallstein

This repository now has a clear separation between the active production app and archived prototype code.

## Main application

The live project is the Django app in [backend](backend).

- [backend/autowallstein_project](backend/autowallstein_project): Django project settings, URLs, and app wiring
- [backend/vehicles](backend/vehicles): vehicle models, views, forms, routes, and admin logic
- [backend/templates](backend/templates): Django templates for public and internal pages
- [backend/static](backend/static): CSS, JS, and static media
- [backend/media](backend/media): uploaded vehicle images and other media files
- [backend/db.sqlite3](backend/db.sqlite3): local SQLite database

## Archived / legacy code

This code is kept for reference only and is not part of the active runtime:

- [legacy/client](legacy/client): old React/Vite prototype
- [legacy/netlify](legacy/netlify): old static website prototype
- [legacy/package.json](legacy/package.json): archived frontend tooling
- [legacy/netlify.toml](legacy/netlify.toml): archived deployment config

## Documentation

- [docs](docs): project notes and structure documentation

## Run the active app

From the project root:

```bash
cd backend
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

The public website and the internal admin area are served by Django from the backend app.

# Project structure

## Active app

The application that is currently in use is the Django project under [backend](../backend).

```text
Auto_Wallstein/
├── backend/
│   ├── .venv/
│   ├── autowallstein_project/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── vehicles/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/
│   ├── templates/
│   ├── static/
│   ├── media/
│   ├── db.sqlite3
│   ├── manage.py
│   ├── requirements.txt
│   └── .env
├── docs/
│   └── PROJECT_STRUCTURE.md
├── legacy/
│   ├── client/
│   ├── netlify/
│   ├── package.json
│   ├── package-lock.json
│   └── netlify.toml
├── README.md
└── .gitignore
```

## Why this structure is better

- only one active application is used at runtime
- the archived prototype code is clearly separated
- Django configuration and business logic are easy to find
- future development is not mixed with old static site code

## Development rule

When working on the project, always treat [backend](../backend) as the source of truth. The contents of [legacy](../legacy) are reference material only unless a separate migration is explicitly planned.

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

## URLs and compatibility

Public pages use German URLs: `/fahrzeuge/`, `/fahrzeuge/<id>/`,
`/kontakt/`, `/ueberuns/`, `/finanzierung/` and `/service/`.

The custom vehicle-management area is under `/verwaltung/`:

- Dashboard: `/verwaltung/`
- Login / logout: `/verwaltung/anmelden/`, `/verwaltung/abmelden/`
- Create: `/verwaltung/fahrzeuge/neu/`
- Edit / images / delete: `/verwaltung/fahrzeuge/<id>/bearbeiten/`,
  `/verwaltung/fahrzeuge/<id>/bilder/`, `/verwaltung/fahrzeuge/<id>/loeschen/`

Django's built-in admin remains at `/admin/`. Management requires the relevant
Django model permissions; authentication alone does not grant access.

Old English public URLs and old management URLs redirect to their canonical
addresses. GET/HEAD requests use HTTP 301; other methods use HTTP 307 to preserve
submitted form data and uploaded files. Query strings are preserved. Existing
management route names remain unchanged, so templates should use Django URL
reversal rather than hard-coded paths. Public links should use `kontakt` and
`ueberuns`, not the legacy `contact` and `about` names.

## Inhalte, Zubehör und Neuigkeiten verwalten

Die kundengerechte Verwaltung bietet drei zusätzliche Bereiche:

- `/verwaltung/zubehoer/`: Verkaufsangebote mit Kategorie, Zustand, Preis,
  Beschreibung und bis zu 12 Bildern. Die kleinste Bildreihenfolge bestimmt das
  Hauptbild. Nur freigegebene, verfügbare Angebote erscheinen unter `/zubehoer/`.
  Anfragen erfolgen über E-Mail oder Telefon; dies ist kein Warenkorb/Onlineshop.
- `/verwaltung/neuigkeiten/`: Beiträge mit Kurztext, Titelbild und Inhalt.
  Entwürfe sind nicht öffentlich. Gespeicherte Beiträge können vor der Freigabe
  in einer geschützten Vorschau geprüft werden. Veröffentlichte Beiträge erscheinen
  unter `/neuigkeiten/` und die letzten drei zusätzlich auf der Startseite.
- `/verwaltung/website/`: vorhandene Startseitentexte, Bildkacheln und bis zu fünf Sliderbilder, Kontaktdaten und Öffnungszeiten. Zuerst **Entwurf speichern**, dann
  **Gespeicherten Entwurf ansehen**, schließlich **Auf Website veröffentlichen**.
  Veraltete Bearbeitungsstände werden beim Speichern zurückgewiesen.

Die Layoutstruktur, rechtliche Texte und technische Verknüpfungen sind bewusst
nicht frei editierbar. Felder erwarten normalen Text, kein HTML. Kontaktdaten
werden auch in Header, Footer, Kontaktseite und Öffnungszeiten übernommen.
Originalbilder können pro Bild wiederhergestellt werden. Bestehende statische
Inhalte dienen als Standard, bis erstmals Inhalte veröffentlicht werden.

Berechtigungen werden über Django-Benutzer/Gruppen zugewiesen: `view_accessory`
plus `add/change/delete_accessory` für Angebote, `view_newsarticle` plus
`add/change/delete_newsarticle` für Beiträge und `change_homepage` für die
Startseite. Superuser haben Zugriff auf alle Bereiche. Reine Inhaltsredakteure
werden nach dem Login direkt in einen für sie zugänglichen Bereich geleitet.

Neue Installationen und Deployments benötigen `python manage.py migrate`.
Uploads werden in `MEDIA_ROOT` gespeichert und müssen zusammen mit der Datenbank
gesichert werden. Bilder dürfen JPEG, PNG oder WebP sein, maximal 10 MB pro Datei.


### Startseiten-Slider

Unter **Website-Inhalte → Startseiten-Slider** stehen die Bildplätze 1–5 zur
Verfügung. Bild 1 ist das Startbild; bei leerem ersten Platz wird das bestehende
Originalbild verwendet. Zusätzliche Plätze sind optional und lassen sich über
**Bild entfernen** leeren. Die Reihenfolge entspricht den Bildplatznummern.
Entwurf, Vorschau und Veröffentlichung gelten auch für die Sliderbilder.

Der Slider zeigt Bilder proportional und vollständig (ohne Beschnitt), mit
maximal 380 Pixel Höhe am Desktop bzw. 300 Pixel mobil. Der Text liegt außerhalb
der Bildfläche. Bei mehreren Bildern erscheinen Vor-/Zurück-Buttons; sie sind
auch per Tastatur bedienbar. Ab zwei Bildern wechselt der Slider alle sechs Sekunden. Eine Pause-Taste stoppt den Wechsel; bei Mausberührung, Tastaturfokus und in ausgeblendeten Tabs pausiert er ebenfalls. Bei reduzierter Bewegung startet er pausiert. Ohne
JavaScript bleibt das erste Bild sichtbar.

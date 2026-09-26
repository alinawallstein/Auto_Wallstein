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
- `/verwaltung/website/`: vorhandene Startseitentexte, Bildkacheln, Kontaktdaten und Öffnungszeiten. Zuerst **Entwurf speichern**, dann
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


### Zentrale Verwaltung und Homepage-Slider

Der zentrale Einstieg ist `/verwaltung/`. Das Dashboard zeigt nur Bereiche,
für die der angemeldete Benutzer Rechte besitzt. Der technische Django-Admin
unter `/admin/` bleibt erhalten. Seine Standardtemplates werden nicht mehr durch
das eigene Verwaltungs-Layout überschrieben.

Unter **Homepage → Slider** (`/verwaltung/homepage/slider/`) lassen sich Slides
mit Bild, optionalem Titel/Untertitel, Bildbeschreibung und optionalem Button
anlegen, bearbeiten, sortieren, aktivieren und löschen. Aktive Slides sind nach
dem Speichern sofort öffentlich. Kleine Reihenfolgen erscheinen zuerst, bei
Gleichstand entscheidet die ID. Es gibt keine zweite Liste von Bildplätzen in
Website-Inhalte. Dort bleiben die Ersatztexte für den Fall ohne aktive Slides.

Die Bildfläche ist auf Desktop maximal 520 px, mobil 280–340 px hoch.
Der Crossfade dauert 600 ms, unabhängig von der eingestellten Standzeit.
Gespeicherte Änderungen erreichen offene Homepage-Tabs im selben Browser
über eine Storage-Nachricht; andere Browser lesen sie beim nächsten Seitenaufruf.

Unter **Homepage → Slider-Einstellungen** kann die Wechselgeschwindigkeit von
2 bis 15 Sekunden eingestellt werden; Standard sind 4 Sekunden. Kein sichtbarer
Pause-/Play-Button. Tastaturfokus, Touch-Gesten und unsichtbare Tabs pausieren
Autoplay. Maus-Hover und Mausklicks auf die Navigation halten es nicht dauerhaft an. Bei reduzierter Bewegung startet kein Autoplay. Pfeile, Dots und
Touch-Swipe bleiben bedienbar; ohne JavaScript bleibt der erste Slide sichtbar.
Bei nur einem Slide werden Navigation und Autoplay weggelassen.

Die vorhandenen Bilder werden von Migration 0004 als Slides übernommen:
veröffentlichte Uploads aktiv, nur im Entwurf gespeicherte Uploads inaktiv.
Originaldateien und alte JSON-Daten werden nicht gelöscht. Die neuen Slides
sind die einzige operative Datenquelle. Die eigene Verwaltung und Django-Admin
verwenden dasselbe Model/Formular. Dateien bleiben beim Löschen eines Slides
im Speicher erhalten, weil übernommene Bilder noch von archivierten Inhalten
referenziert werden können.

### Kundenanfragen und Antworten

`/verwaltung/anfragen/` bietet Suche, Statusfilter, Datumsortierung und Seiten.
Die Originalnachricht ist schreibgeschützt, auch im technischen Admin. Beim Öffnen
wird eine neue Anfrage für Mitarbeiter mit Änderungsrecht als gelesen markiert.
Die Statuswerte lauten Neu, Gelesen, In Bearbeitung, Beantwortet und Erledigt.
Bestehende Anfragen erhalten beim Upgrade zunächst Neu, weil bisher kein
Lesestatus gespeichert wurde. Der ursprüngliche Fahrzeugbetreff wird archiviert.

Unter **Antworten** sind Empfänger und Betreff vorgegeben. Jede Antwort wird
als eigener Datensatz mit Text, Mitarbeiter und Versandstatus gespeichert.
Erfolgreiche SMTP-Übergabe markiert die Anfrage als Beantwortet; sie ist kein
Nachweis einer tatsächlichen Zustellung beim Empfänger. Fehler erhalten den Text
im Verlauf und zeigen eine verständliche Meldung. Doppeltes Absenden desselben
Formulars erzeugt keine zweite Mail. Nach Prozessabbruch kann der Status
„Ergebnis offen“ verbleiben; vor erneutem Versand den Mailserver prüfen.
Dies ist ein ausgehender Antwortverlauf, keine Synchronisation eingehender
E-Mails aus einem Postfach.

Die vorhandene Django-Mailkonfiguration wird verwendet. Konfigurationsschlüssel
stehen in `backend/.env.example`. Ohne SMTP bleibt Konsolen-/Testbetrieb sichtbar;
Antworten werden dann nicht als erfolgreich versendet oder beantwortet markiert.
SMTP-Geheimnisse ausschließlich in der Serverumgebung bzw. `.env` setzen.
Benachrichtigungsfehler zerstören keine gespeicherte Kontaktanfrage.

Zusätzliche Rechte für Mitarbeiter (nicht zwingend `is_staff`):
- Kundenanfragen lesen: `view_customerinquiry`.
- Status ändern: zusätzlich `change_customerinquiry`.
- Antworten senden: zusätzlich `add_inquiryreply`.
- Slider: `view_heroslide` und je nach Aufgabe `add/change/delete_heroslide`.
- Wechselgeschwindigkeit: `change_slider_settings`.

Superuser besitzen alle Rechte. Für `/admin/` ist zusätzlich der Django-Staffstatus
notwendig. Abmelden und alle schreibenden Aktionen verwenden POST und CSRF.

Nach Übernahme der Änderungen:

```sh
cd backend
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py test --noinput
node --test tests_js/*.test.cjs
```

Datenbank und MEDIA_ROOT vor Deployments gemeinsam sichern. Im Produktivbetrieb
müssen Medien/Static Files vom Webserver bzw. Storage ausgeliefert werden;
Djangos Entwicklungsserver ist dafür nicht vorgesehen.

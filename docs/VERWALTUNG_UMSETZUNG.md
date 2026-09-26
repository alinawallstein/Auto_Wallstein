# Auto Wallstein – zentrale Verwaltung

Stand: 26. September 2026. Die damaligen Slider-Angaben wurden anschließend
durch [die Slider-Überarbeitung](SLIDER_UEBERARBEITUNG.md) ersetzt.

## Ergebnis und Architektur

`/verwaltung/` ist der zentrale Einstieg für Händler. Die Navigation umfasst
Dashboard, Fahrzeuge, Kundenanfragen, Homepage sowie die bestehenden Bereiche
Zubehör und Neuigkeiten. Nur berechtigte Bereiche werden angezeigt. Auf dem
Smartphone wird das vorhandene Navigationsscript für ein aufklappbares Menü
wiederverwendet. `/admin/` bleibt für technische Administration erhalten.

Die beiden Verwaltungsbereiche entstanden durch die Kombination des automatisch
registrierten Django-Admins mit eigenen, separat entwickelten Händleransichten.
Fahrzeuge und Fahrzeugbilder waren bereits in beiden Bereichen erreichbar;
Zubehör, Neuigkeiten und Homepage-Texte über die eigene Verwaltung. Kundenanfragen,
Benutzer/Gruppen und gespeicherte Fahrzeug-KI-Texte waren über `/admin/` zugänglich.
Kundenanfragen und Slider wurden jetzt in den Händlerarbeitsablauf übernommen;
Benutzer-/Rechteadministration und die bestehende technische KI-Textpflege bleiben
erhalten, ohne neue Dummy-Funktionen in der Navigation.

Es gibt eine aktive Django-App `vehicles`. Neue fachliche Module trennen
Dashboard, Slider-Verwaltung, Anfrageformulare und Mailversand, ohne neue App,
Slider-Library oder zusätzliche Laufzeitabhängigkeit einzuführen.

Datenfluss des Sliders:

`Verwaltung oder Django-Admin → gemeinsames HeroSlideForm → HeroSlide → Home-View/Selector → Template-Partial → vorhandenes Vanilla-JavaScript`

Die Wechselzeit liegt am vorhandenen Singleton `Homepage.slider_interval`.
Das Template übergibt ausschließlich den validierten Zahlenwert über `data-interval`.
Die Hauptseite lädt aktive Slides in einer geordneten Query. Die alte JSON-Bildliste
ist keine zweite operative Sliderquelle mehr.

## Bedienung

### Kundenanfragen

1. `/verwaltung/` öffnen und anmelden.
2. Unter **Kundenanfragen → Neue Anfragen** oder **Alle Anfragen** die Inbox öffnen.
3. Suche, Statusfilter und Datumsortierung verwenden; größere Listen werden paginiert.
4. **Öffnen** zeigt Originalnachricht, Kontaktdaten, Fahrzeug, Datum und Status.
5. Mitarbeiter mit Änderungsrecht markieren neue Anfragen beim Öffnen als gelesen.
   **Status speichern** erlaubt Neu, Gelesen, In Bearbeitung, Beantwortet und Erledigt.
6. **Antworten** führt zum Antwortformular. Empfänger und Betreff werden vom Server
   übernommen und können nicht durch zusätzliche POST-Felder umgebogen werden.
7. **Antwort per E-Mail senden** sendet über die bestehende Django-Mailkonfiguration.
   Der separate Antwortverlauf enthält Text, Empfänger, Betreff, Mitarbeiter,
   Versandstatus und Zeitstempel. Originalnachricht und Kontaktdaten bleiben unverändert.

Erfolgreicher Versand bedeutet die Übergabe an das konfigurierte Mailbackend,
nicht den Nachweis der Zustellung im Postfach. Erst im echten Versandbetrieb
wird die Anfrage automatisch als beantwortet markiert. Im Konsolen-/Testbetrieb
steht dies sichtbar im Formular und Verlauf; der Vorgang bleibt offen.

Ein Versandfehler erhält den geschriebenen Text im Verlauf. Derselbe Formular-Token
kann nicht zweimal senden. Nach einem Prozessabbruch kann ein Versand als
„Ergebnis offen“ stehen bleiben; vor einem neuen Versuch den Mailserver prüfen.
Das System liest keine Antworten aus einem externen E-Mail-Postfach ein.

### Homepage-Slider

1. **Homepage → Slider → Slide hinzufügen** öffnen.
2. JPEG, PNG oder WebP bis 10 MB auswählen. Optional Titel, Untertitel,
   Bildbeschreibung sowie Button-Text und Link eingeben.
3. **Aktiv** ankreuzen und speichern: Der Slide ist sofort öffentlich.
4. Kleine Zahlen bei **Reihenfolge** erscheinen zuerst; bei Gleichstand entscheidet die ID.
5. **Bearbeiten** erlaubt Austausch des Bildes und Deaktivierung. Ein leerer Upload
   behält das gespeicherte Bild. **Löschen** verlangt eine Bestätigung per POST.
6. **Homepage → Slider-Einstellungen** erlaubt 2–30 Sekunden, Standard 4 Sekunden.

Der sichtbare Pause-/Play-Button ist entfernt. Pfeile, Dots, Tastatur und Swipe
bleiben erhalten. Autoplay pausiert bei Fokus, Mausinteraktion und in einem
unsichtbaren Tab. Bei reduzierter Bewegung findet kein automatischer Wechsel statt.
Mit einem Slide gibt es keine überflüssige Navigation; ohne aktiven Slide wird
der bestehende Ersatzbereich verwendet. Ohne JavaScript bleibt der erste Slide sichtbar.

## Rechte

Alle Verwaltungsansichten benötigen eine Anmeldung und passende Model-Rechte.
Staffstatus ist nur für `/admin/` notwendig, nicht für die eigene Verwaltung.
Superuser besitzen alle Rechte. Normale Mitarbeiter erhalten gezielt:

| Aufgabe | Django-Rechte |
| --- | --- |
| Kundenanfragen lesen | `view_customerinquiry` |
| Status ändern | zusätzlich `change_customerinquiry` |
| Antworten senden | zusätzlich `add_inquiryreply` |
| Slides lesen | `view_heroslide` |
| Slides pflegen | zusätzlich je nach Aufgabe `add_heroslide`, `change_heroslide`, `delete_heroslide` |
| Geschwindigkeit ändern | `change_slider_settings` |

Bestehende Fahrzeug-, Zubehör-, Neuigkeiten- und Inhaltsrechte bleiben erhalten.
Es wurden keine Benutzer oder Berechtigungen automatisch erweitert.

## Datenbank und Migrationen

- Das bereits angelegte `HeroSlide` wird weiterverwendet.
- `0005_inquiryreply_alter_homepage_options_and_more`: Antwortverlauf, Anfrage-Status,
  unveränderlicher Betreff, Slider-Intervall mit Datenbankgrenzen und Einstellungsrecht.
- `0006_inquiry_subject_snapshot`: archiviert den bisherigen Fahrzeugbetreff
  bestehender Anfragen. Nachrichtentexte werden nicht verändert.
- Bestehende Anfragen erhalten zunächst den Status Neu, da zuvor kein Lesestatus existierte.
- Beide Migrationen sind in der lokalen Projektdatenbank bereits ausgeführt.
- Vorherige SQLite-Sicherung:
  `/var/folders/qd/7b5vxwq54cgghb8vdj0dnb180000gn/T/wallstein-before-central-admin-hmq267vj/db.sqlite3`.
- Ein Vergleich gegen die Sicherung bestätigte den unveränderten Erhalt der
  bisherigen Anfrage samt Originaldaten sowie beider vorhandener Slides.

## E-Mail-Konfiguration und nächste Schritte

Die vorhandene Umgebung verwendet bereits das SMTP-Backend; SMTP-Host und Absender
sind gesetzt. Zugangsdaten wurden weder angezeigt noch verändert. Der neue Code
verwendet diese Konfiguration. Ergänzt wurden optionale SSL- und Timeout-Einstellungen.
Ein echter Versand an Kunden wurde nicht ausgelöst; Transporttests waren isoliert.
Die SMTP-Erreichbarkeit und Zugangsdaten sind dadurch nicht live verifiziert.

`backend/.env.example` dokumentiert:
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`,
`INQUIRY_NOTIFICATION_EMAIL` und den optionalen `EMAIL_BACKEND`-Override.
TLS und SSL nicht gleichzeitig aktivieren. Geheimnisse gehören ausschließlich
in `.env` oder die Serverumgebung.

Bei Übernahme auf einen anderen Server zuerst Datenbank und MEDIA_ROOT sichern,
dann im Projektverzeichnis:

```sh
cd backend
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
```

Anschließend den Django-Prozess über den bisherigen Betriebsweg neu starten und
die geänderten Static Files über den bestehenden Webserver-/Deploymentweg ausliefern.
Mitarbeiterrechte zuweisen. Neue Slides müssen ausdrücklich aktiviert werden.
Die lokalen Migrationen müssen nicht noch einmal ausgeführt werden.

## Prüfungen

- 108 Django-Tests bestanden, einschließlich bestehender Fahrzeugverwaltung.
- 15 JavaScript-Tests bestanden.
- `manage.py check`: keine Fehler oder Warnungen.
- `makemigrations --check --dry-run`: keine fehlenden Migrationen.
- `git diff --check`: sauber.
- Chrome-Browserprüfung mit eigener Testdatenbank und simuliertem Mailversand:
  eigener Verwaltungs-Upload und technischer Admin, null/ein/mehrere Slides,
  konfigurierte Autoplay-Zeit, Pfeile, Dots, Tastatur, echtes Touch-Swipe,
  No-JavaScript-Fallback und reduzierte Bewegung.
- Darstellung bei 390, 768, 1440 und 1920 Pixeln geprüft; kein horizontaler Seitenüberlauf.
- Anfrage über Kontaktformular, schreibgeschützte Detailansicht und Antwortverlauf
  auch im Browser geprüft. Mobile Navigation öffnet und schließt einschließlich Escape.
- Keine JavaScript-Laufzeitfehler auf den geprüften Seiten.
- Der isolierte Prüfserver und seine Testdaten sind getrennt von echten Inhalten.

## Festgestellte, bewusst nicht vollständig bearbeitete Punkte

### Kritisch vor Produktivbetrieb

`manage.py check --deploy` meldet **security.W009** für einen zu schwachen
SECRET_KEY sowie **W004/W008/W012/W016** für fehlende HSTS-, HTTPS-Redirect- und
Secure-Cookie-Einstellungen. Die bestehende Konfiguration wurde nicht still
geändert: Schlüsselrotation und Proxy-/HTTPS-Konfiguration müssen zur tatsächlichen
Betriebsumgebung passen. Ein eventuell vorgeschalteter Proxy wurde nicht geprüft.

### Sollte verbessert werden

- In den Django-Settings fehlt `STATIC_ROOT`; eine collectstatic-basierte
  Produktionsauslieferung ist im Projekt nicht vollständig definiert.
  Medien werden in der Django-URL-Konfiguration nur im Entwicklungsmodus ausgeliefert.
  Bei `DEBUG=False` muss ein Webserver oder Storage `/static/` und `/media/` übernehmen.
- Das Kontaktformular versendet Empfangsbestätigungen, hat im vorhandenen Code
  aber keinen erkennbaren Schutz gegen wiederholte automatisierte Einsendungen.
  Die vorhandene Funktion wurde erhalten; mögliche vorgeschaltete Schutzmaßnahmen
  sind nicht aus dem Repository ersichtlich.
- Öffentliche Bilder werden als Originaldateien ausgeliefert. Beispielsweise ist
  `finanzierung.jpg` ungefähr 4,6 MB groß. Responsive Bildderivate wurden nicht
  nachträglich über bestehende Uploads geschrieben.

### Optional

- Ein Hintergrundjob für Mailversand kann bei höherem Anfrageaufkommen die
  Wartezeit verkürzen. Aktuell wird synchron mit begrenztem SMTP-Timeout versendet.
- Die Seite verwendet weiterhin sowohl den externen Bestands-iframe als auch
  interne Fahrzeugangebote; diese fachliche Bestandsentscheidung wurde nicht geändert.
- Nicht mehr referenzierte Uploaddateien werden nicht automatisch gelöscht,
  um insbesondere übernommene/archivierte Bildreferenzen nicht zu beschädigen.

## Dateien dieser Verwaltungs-Erweiterung

| Status | Datei |
| --- | --- |
| Geändert | [README.md](../README.md) |
| Geändert | [backend/.env.example](../backend/.env.example) |
| Geändert | [backend/autowallstein_project/settings.py](../backend/autowallstein_project/settings.py) |
| Geändert | [backend/static/css/hero-slider.css](../backend/static/css/hero-slider.css) |
| Geändert | [backend/static/css/management.css](../backend/static/css/management.css) |
| Geändert | [backend/static/js/hero-slider.js](../backend/static/js/hero-slider.js) |
| Geändert | [backend/templates/admin/dashboard.html](../backend/templates/admin/dashboard.html) |
| Geändert | [backend/templates/admin/homepage_form.html](../backend/templates/admin/homepage_form.html) |
| Geändert | [backend/templates/management/base.html](../backend/templates/management/base.html) |
| Geändert | [backend/templates/partials/hero_slider.html](../backend/templates/partials/hero_slider.html) |
| Geändert | [backend/templates/public/home.html](../backend/templates/public/home.html) |
| Geändert | [backend/tests_js/hero-slider.test.cjs](../backend/tests_js/hero-slider.test.cjs) |
| Geändert | [backend/vehicles/admin.py](../backend/vehicles/admin.py) |
| Geändert | [backend/vehicles/content.py](../backend/vehicles/content.py) |
| Geändert | [backend/vehicles/content_views.py](../backend/vehicles/content_views.py) |
| Geändert | [backend/vehicles/models.py](../backend/vehicles/models.py) |
| Geändert | [backend/vehicles/test_catalog.py](../backend/vehicles/test_catalog.py) |
| Geändert | [backend/vehicles/test_slider.py](../backend/vehicles/test_slider.py) |
| Geändert | [backend/vehicles/urls_management.py](../backend/vehicles/urls_management.py) |
| Geändert | [backend/vehicles/views.py](../backend/vehicles/views.py) |
| Neu | [backend/templates/management/inquiry_detail.html](../backend/templates/management/inquiry_detail.html) |
| Neu | [backend/templates/management/inquiry_list.html](../backend/templates/management/inquiry_list.html) |
| Neu | [backend/templates/management/pagination.html](../backend/templates/management/pagination.html) |
| Neu | [backend/templates/management/slider_delete.html](../backend/templates/management/slider_delete.html) |
| Neu | [backend/templates/management/slider_form.html](../backend/templates/management/slider_form.html) |
| Neu | [backend/templates/management/slider_list.html](../backend/templates/management/slider_list.html) |
| Neu | [backend/templates/management/slider_settings.html](../backend/templates/management/slider_settings.html) |
| Neu | [backend/vehicles/inquiry_forms.py](../backend/vehicles/inquiry_forms.py) |
| Neu | [backend/vehicles/inquiry_mail.py](../backend/vehicles/inquiry_mail.py) |
| Neu | [backend/vehicles/inquiry_views.py](../backend/vehicles/inquiry_views.py) |
| Neu | [backend/vehicles/management.py](../backend/vehicles/management.py) |
| Neu | [backend/vehicles/migrations/0005_inquiryreply_alter_homepage_options_and_more.py](../backend/vehicles/migrations/0005_inquiryreply_alter_homepage_options_and_more.py) |
| Neu | [backend/vehicles/migrations/0006_inquiry_subject_snapshot.py](../backend/vehicles/migrations/0006_inquiry_subject_snapshot.py) |
| Neu | [backend/vehicles/slider_forms.py](../backend/vehicles/slider_forms.py) |
| Neu | [backend/vehicles/slider_views.py](../backend/vehicles/slider_views.py) |
| Neu | [backend/vehicles/test_management.py](../backend/vehicles/test_management.py) |
| Neu | [docs/VERWALTUNG_UMSETZUNG.md](../docs/VERWALTUNG_UMSETZUNG.md) |

`backend/db.sqlite3` wurde durch die beschriebenen Migrationen aktualisiert.

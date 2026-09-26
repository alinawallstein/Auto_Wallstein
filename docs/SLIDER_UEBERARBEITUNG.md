# Homepage-Slider – kompakte Überarbeitung

## Ursache

Die gespeicherte Standzeit betrug bei der Analyse **2 Sekunden**. Django übergab
sie korrekt, JavaScript multiplizierte sie genau einmal mit 1000. Die bisherige
CSS-Animation dauerte 450 ms. Weder Bootstrap-Carousel noch ein zweites aktives
Slidersystem waren vorhanden.

Die tatsächlichen Stopper lagen in der Interaktionslogik:

- `mouseenter` stoppte den Timer auf der gesamten großen Bildfläche unbegrenzt.
- Jeder Fokus innerhalb des Sliders stoppte Autoplay, auch der nach einem Mausklick
  auf Pfeile oder Dots zurückbleibende Button-Fokus.
- `mouseleave`, `pointerleave` und Fokusereignisse setzten die volle Wartezeit neu.
- Es gab keinen Schutz gegen erneute Initialisierung desselben Elements.

Damit konnte die eingestellte kurze Standzeit optisch wirkungslos erscheinen.
Eine exakt 20–30 Sekunden lange CSS-Animation war nicht vorhanden.

Die Größe entstand durch `min-height: clamp(28rem, 43vw, 44rem)`, eine zusätzliche
Steuerleiste und auf Mobilgeräten untereinander angeordnete Bild- und Textblöcke.

## Neue Implementierung

Das bestehende `HeroSlide`-Model und seine Bildverwaltung bleiben erhalten.
CSS und JavaScript wurden direkt ersetzt, nicht durch überschreibende Zusatzregeln
oder einen zweiten Timer ergänzt.

- Desktop: 420–520 px; bei 1440 px Breite ungefähr 490 px.
- Tablet: 360–420 px; bei 834 px Breite ungefähr 375 px.
- Smartphone: 280–340 px; bei 390 px Breite ungefähr 320 px.
- Bilder durchgehend `object-fit: cover`, keine Verzerrung; motivabhängiger Beschnitt.
- Titel, Text und Link liegen über einem dunklen Verlauf. Sehr lange Texte bleiben
  innerhalb des begrenzten Textbereichs scrollbar, statt die Homepage aufzublähen.
- Pfeile liegen dezent über dem Bild, Dots am unteren Bildrand, keine separate hohe Leiste.
- Keine Pause-/Play-Schaltfläche und keine Hover-Pausenlogik.
- Tastaturfokus, aktive Touch-Gesten und unsichtbare Tabs unterbrechen Autoplay gezielt.
- Reduzierte Bewegung deaktiviert automatische Wechsel und Übergangsanimationen.

Es existiert genau ein Autoplay-Timeout. Vor jedem Ersatz wird dieser gelöscht.
Der Ablauf nach einem Wechsel besteht aus **600 ms Crossfade + gespeicherter Standzeit**.
Die CSS-Dauer wird aus dem berechneten Stil gelesen und nicht zusätzlich in JS gepflegt.
Initial erscheint das nächste Bild nach der reinen Standzeit. Danach sind die
Wechselanfänge bei Standardwerten etwa 4,6 Sekunden auseinander: 0,6 Sekunden
Übergang und 4 Sekunden vollständig sichtbares Bild.

Ein Initialisierungsmarker verhindert doppelte Listener/Timer beim erneuten Laden
des Scripts. `pagehide` räumt den Timer auf; Wiederherstellung aus dem Browsercache
startet ihn sauber neu. Swipe verwendet Pointer Events ohne externe Bibliothek.
Der Textbereich erhält ebenfalls `touch-action: pan-y`, damit sein Scrollcontainer
horizontale Wischgesten nicht abfängt.

## Backend und Sekunden

Einstellung: `/verwaltung/homepage/slider/einstellungen/`.

Die einzige persistente Quelle ist `Homepage.slider_interval`: Standard **4**, erlaubter
Bereich **2–15 Sekunden**. Die vorhandene Auswahl von 2 Sekunden wurde nicht überschrieben.
Die View und der Context Processor übernehmen den Wert; das Template schreibt ihn
escaped in `data-interval`. JavaScript wandelt Sekunden einmal in Millisekunden um.

Eine erfolgreiche Speicherung wird über `slider-settings.js` an andere offene Tabs
auf derselben Origin gemeldet. Dieses kleine Script bedient keine Slides und erzeugt
keine Timer. Es überträgt nur den bereits gespeicherten Wert, niemals die ungespeicherte
Formulareingabe. Offene Homepage-Tabs desselben Browsers starten ihren einzigen Timer
mit dem neuen Wert. Bei blockiertem Browser-Speicher oder in anderen Browsern wird der
neue Wert beim nächsten Seitenaufruf verwendet; es gibt kein zusätzliches Polling.

Migration `0007` setzt Validator und Datenbankgrenze auf 15 Sekunden. Frühere Werte
über 15 werden vor Aktivierung der neuen Grenze auf 15 begrenzt. Bilder, Reihenfolge,
Texte, Aktivierung und alle anderen Homepage-Inhalte werden nicht verändert.
Die Migration ist lokal bereits ausgeführt, nach einer SQLite-Sicherung.

## Geänderte Dateien

- `backend/static/js/hero-slider.js`
- `backend/static/css/hero-slider.css`
- `backend/templates/partials/hero_slider.html`
- `backend/templates/public/home.html`
- `backend/templates/management/slider_settings.html`
- `backend/vehicles/models.py`
- `backend/vehicles/slider_forms.py`
- `backend/tests_js/hero-slider.test.cjs`
- `backend/vehicles/test_management.py`
- `README.md`
- `docs/VERWALTUNG_UMSETZUNG.md` – Verweis auf diesen aktualisierten Bericht

Neu:

- `backend/static/js/slider-settings.js`
- `backend/vehicles/migrations/0007_remove_homepage_homepage_slider_interval_range_and_more.py`
- `docs/SLIDER_UEBERARBEITUNG.md`

`backend/db.sqlite3` wurde durch die Migration aktualisiert.

## Prüfung

- 108 Django-Tests bestanden; nach Ergänzung der Prüfung gegen das Übertragen
  ungespeicherter Werte nochmals 15 relevante Slider-/Verwaltungstests bestanden.
- 18 JavaScript-Tests bestanden, einschließlich Hover/Mausfokus, mehrfacher Navigation,
  einzelner Timer, Neuinitialisierung, Cache-Rückkehr und Geschwindigkeitsnachricht.
- `manage.py check`, `makemigrations --check --dry-run` und `git diff --check` bestanden.
- Native Browserprüfung auf separater Testdatenbank: Standzeiten, Übergang, Backendänderung
  ohne Homepage-Reload, maximal ein Timer und Darstellung bei 320/390/834/1280/1440/1920 px.

Für andere Installationen nach Sicherung der Datenbank aus `backend/`:

```sh
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
```

Anschließend die aktualisierten Static Files ausliefern und den Django-Prozess neu starten.

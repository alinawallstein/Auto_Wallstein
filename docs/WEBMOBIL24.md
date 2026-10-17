# WebMobil24 – Einrichtung und lesender Verbindungstest

Stand der ursprünglichen Einrichtung: 10.10.2026. Import-Erweiterung: 12.10.2026 (siehe unten). Die aktive Anwendung liegt in backend/ (Django, App vehicles).
Es wurden keine AGENTS.md-Dateien im Projekt oder seinen übergeordneten Verzeichnissen gefunden.
Der Befehl ist in der separaten App webmobil24_integration registriert, weil
vehicles.management bereits die Verwaltungsseiten implementiert. Der Client
liegt in vehicles/webmobil24.py und verwendet ausschließlich GET; der Befehl greift weder auf Django-Modelle
noch auf Datenbank, Bilder oder öffentliche Seiten zu. Kein Import, kein Abgleich.

## Quellen und bestätigter Vertrag

- [Quick Start](https://webmobil24.atlassian.net/wiki/spaces/WM24API/pages/1414692865/Quick+Start+Guide)
- [Authentifizierung](https://webmobil24.atlassian.net/wiki/spaces/WM24API/pages/1414758421/Authentication)
- [OpenAPI 1.3.0](https://app.swaggerhub.com/apis/WebMobil24/WM24-API/1.3.0)

Im Browser gelesen. Bearer-Token in Authorization; getrennte Tokens für Test und
Produktion werden von WebMobil24 vergeben. Testdaten können veraltet sein.
Basis-URLs aus OpenAPI: https://testapi.webmobil24.com/rest und
https://api.webmobil24.com/rest. Keine frei konfigurierbare Ziel-URL, damit der Token
nicht versehentlich an einen anderen Host gesendet wird; Redirects werden abgewiesen.

| Zweck | GET-Endpunkt | Verwendete Parameter |
|---|---|---|
| Freigegebene Händler | /dealers | offset, limit |
| Aktive Fahrzeuge | /dealers/{dealerId}/listings | offset, limit, language=DE, onlyActiveAds=true |
| Fahrzeugdetail | /dealers/{dealerId}/listings/{listingId} | language=DE |
| Bilder | /dealers/{dealerId}/listings/{listingId}/images | keine Queryparameter |

Listen sind JSON-Arrays; Fahrzeugdetails ein Objekt. Listen können X-Total-Count
und X-Result-Count enthalten. Bilder besitzen id und url. HTTP 404 bedeutet laut
Spezifikation fehlende Ressource oder keine Ergebnisse; der Test meldet dies als
Fehler und behauptet keinen erfolgreichen leeren Bestand.
Eine feste Anbieterquote oder maximale Seitengröße ist in den gelesenen
Endpoint-Beschreibungen nicht angegeben. Die Grenzen unten sind lokale Grenzen,
keine behaupteten Anbietergrenzen.

## Einrichtung

Vorhandene backend/.env ergänzen (nicht überschreiben):

```dotenv
WEBMOBIL24_ENV=test
WEBMOBIL24_TOKEN=<selbst lokal eintragen>
WEBMOBIL24_DEALER_ID=<nach Händlerabfrage eintragen>
WEBMOBIL24_TIMEOUT=15
```

settings.py lädt .env bereits mit python-dotenv; vorhandene Prozessvariablen haben
Vorrang. .env ist bereits in .gitignore ausgeschlossen. Der Token wird weder in
repr, Befehlsausgabe, Fehlermeldungen noch im Browser ausgegeben. Keine neue
Abhängigkeit erforderlich: der HTTP-Client verwendet die Python-Standardbibliothek.
Für getrennte Umgebungen jeweils den passenden Token selbst lokal setzen.

```sh
cd /Users/alinawallstein/Auto_Wallstein/backend
.venv/bin/python manage.py test_webmobil24 --list-dealers
```

Dieser Aufruf zeigt nur Händler-ID und Firmenname der freigegebenen Händler,
keine vollständigen Händlerdatensätze oder Export-Zugangsdaten. Passende ID in
.env setzen. Bei mehreren Händlern nichts automatisch auswählen.

```sh
.venv/bin/python manage.py test_webmobil24
.venv/bin/python manage.py test vehicles.test_webmobil24
```

Standard: eine Seite mit höchstens zehn aktiven Fahrzeugen, anschließend Details
und Bildadressen des ersten Fahrzeugs. Keine Bilddownloads. Ein leeres Array
überspringt Details/Bilder ausdrücklich. Optional --page-size 1–100 und
--max-pages 1–10; maximal 1000 Einträge und zwei zusätzliche Detail-/Bildabrufe.
Mit --list-dealers entfallen die beiden zusätzlichen Abrufe. Der Test ist eine
Stichprobe und keine Prüfung sämtlicher Fahrzeuge. Er stoppt bei kurzen Seiten,
erreichter Gesamtzahl oder lokalem Seitenlimit und meldet dies.

Timeout 1–60 Sekunden pro Anfrage, Antwortlimit 8 MiB, Prüfung von JSON,
Antwortstruktur, IDs, Pagination-Headern und HTTPS-Bildadressen. HTTPS-Adressen
werden syntaktisch validiert, ihre Erreichbarkeit wird nicht behauptet.
HTTP 401/403/404/429, Serverfehler, Redirects und Netzwerkfehler führen zu einem
Fehlerstatus ohne rohe Antworttexte oder Zugangsdaten. Keine automatischen
Wiederholungen; bei 429 später erneut testen, statt zusätzliche Last zu erzeugen.

Falls der Anbieter bestätigt, dass der Zugang nur für Produktion gilt, passenden
Token lokal setzen und ausdrücklich ausführen:

```sh
.venv/bin/python manage.py test_webmobil24 --environment production --list-dealers
.venv/bin/python manage.py test_webmobil24 --environment production
```

Kein stiller Wechsel zur Produktion: ein 401 beweist nicht, dass der Token dort gilt.
Auch Produktionsaufrufe bleiben ausschließlich lesend.

## Spätere Zuordnung zu den vorhandenen Modellen

Planungsstand vom 10.10.2026, inzwischen durch die Import-Erweiterung unten umgesetzt. Eine separate externe Identität (Anbieter, dealerId,
listingId) sollte später eindeutig gespeichert werden; listingId nicht ungeprüft
als vorhandene internal_number verwenden. offerReferenceId kann ein Kandidat für
die interne Nummer sein, benötigt aber einen Kollisions- und Leerwertcheck.

| Dokumentiertes API-Feld | Bestehendes Vehicle-Feld / Prüfung |
|---|---|
| make, model, modelVersion/modelName | brand, model, variant; Bedeutung abstimmen |
| firstRegistrationDate, productionYear | first_registration, year; fehlende Werte nicht erfinden |
| mileage, power, cylinderCapacity | mileage, power_kw (Einheit zusätzlich bestätigen), engine_capacity |
| transmission, fuelCategory/primaryFuelTypeId | transmission, fuel_type; Referenzwerte übersetzen |
| vehicleType/bodyTypeId | vehicle_type; Referenz-Mapping festlegen |
| doorCount, seatCount | doors, seats |
| bodyColorName/bodyColor, upholsteryType | exterior_color, interior_equipment |
| vin, previousOwnersCount, nextInspectionDate | vin, previous_owners, hu_valid_until |
| prices (type PUBLIC, currency EUR) | sale_price mit Decimal; Preis auf Anfrage gesondert behandeln |
| description, equipment, standardEquipment, specialEquipment | description, equipment; Referenzen auflösen, Textformat beachten |

power_ps erfordert eine bestätigte Einheit und definierte Rundung. purchase_price
ist ein Pflichtfeld im Modell: kein dokumentierter Einkaufspreis, daher keine
Übernahme des Händlerpreises als Einkaufspreis. Pflichtfelder ohne API-Wert müssen
im separaten Importkonzept gelöst werden. status, is_published und public_visible
erfordern eine ausdrücklich festgelegte Freigabepolitik; vorhandene lokale Werte
nicht automatisch überschreiben. API ACTIVE entspricht nicht automatisch dem
lokalen Verkaufsstatus AVAILABLE.

VehicleImage benötigt eine lokal gespeicherte Datei; eine API-URL lässt sich nicht
direkt in das ImageField importieren. Später nur nach vereinbartem Downloadkonzept
(Hostprüfung, Größenlimit, Bildvalidierung, externe Bild-ID und Sortierung).
Vorhandene Bilder, Hauptbild und manuelle Reihenfolge erhalten; kein automatisches
Löschen. Der aktuelle Client liefert ausschließlich validierte Metadaten.

## Testresultat

- 15 neue simulierte API-/Befehlstests bestanden.
- Gesamte Django-Suite: 145 Tests bestanden (15,232 Sekunden).
- Django-Systemcheck: keine Probleme.
- .env wird von Git ignoriert; keine Zugangsdaten in den neuen Dateien.
- Echter Test: --list-dealers am 10.10.2026 aufgerufen; wegen fehlendem
  WEBMOBIL24_TOKEN vor einem Netzwerkabruf beendet. Daher noch kein Nachweis
  erfolgreicher Authentifizierung oder echter Fahrzeug-/Bildabrufe.
- Noch erforderlich: Test-Token lokal eintragen, freigegebene Händler abrufen,
  passende dealerId auswählen und eintragen, echten Verbindungstest wiederholen.

Die Suite nutzte eine separate Django-Testdatenbank. Vorhandene Änderungen an
Datenbank, Seiten, Bildern und anderen Projektdateien waren bereits vor dieser
Einrichtung vorhanden und wurden nicht überschrieben. Kein produktiver Import
und keine Migration wurden ausgeführt.

## Import-Erweiterung vom 12.10.2026

Die Produktionsverbindung für Händler 3664 (Auto-Wallstein) wurde erfolgreich
geprüft. Die API meldet 28 aktive Fahrzeuge. Die neuen Funktionen befinden sich
in `webmobil24_integration/importer.py` und dem Management-Befehl
`import_webmobil24`.

### Bedienung

```sh
cd /Users/alinawallstein/Auto_Wallstein/backend
# Vollständige Datenprüfung, ohne lokale Änderungen oder Bilddownloads:
.venv/bin/python manage.py import_webmobil24
# Fahrzeuge lokal speichern, Bilder herunterladen:
.venv/bin/python manage.py import_webmobil24 --apply
```

Die Konfiguration verwendet `WEBMOBIL24_TOKEN`, `WEBMOBIL24_ENV`,
`WEBMOBIL24_DEALER_ID` und `WEBMOBIL24_TIMEOUT` aus `.env`. Geheimnisse bleiben dort.
Alle Anbieteraufrufe verwenden GET. Kein Schreiben oder Löschen bei Webmobil24.

Neue Fahrzeuge erhalten Status **In Vorbereitung**, `is_published=False` und
`public_visible=False`. In der Verwaltung unter **Fahrzeuge** nach `WM24` suchen.
Daten und Bilder prüfen; die neue **Vorschau** zeigt die Fahrzeugdetailseite
geschützt vor Veröffentlichung. Vorschau erfordert Lese- und Änderungsrechte,
ist nicht indexierbar, nicht cachebar und bietet keine Kundenanfragebuttons.
Für eine bewusste Veröffentlichung anschließend unter Fahrzeugdaten den Status
**Verfügbar** setzen und unter Veröffentlichung die Website-Freigabe aktivieren.
Der Import veröffentlicht niemals automatisch.

### Zuordnung und Erhalt vorhandener Daten

- Eindeutige externe Identität: Umgebung + Händler-ID + Listing-ID. Getrennte
  Tabelle `ImportedListing`, verknüpft mit genau einem lokalen Fahrzeug.
- Neue interne Nummer: `WM24-<Umgebung>-<Händler-ID>-<Listing-ID>`. Vorhandene
  manuelle Fahrzeuge werden nicht anhand ähnlicher Namen oder FIN zusammengeführt.
- Ausstattungs-IDs werden über `/references/equipment?language=DE` in Text
  übersetzt; aktive Standard-/Sonderausstattungen werden ergänzt.
- Markdown-Hervorhebungen und Escapezeichen aus Beschreibungen werden in normalen
  Text umgewandelt. Originaldaten bleiben ausschließlich serverseitig am Importdatensatz.
- `power` wird als kW übernommen (am echten Datensatz mit dessen Beschreibung
  abgeglichen, z. B. 190 kW / 258 PS). PS werden aus kW berechnet und gerundet.
- Öffentliches EUR-Angebot wird als Verkaufspreis übernommen; andere Preisarten
  werden nicht als Verkaufspreis verwendet. Preis auf Anfrage oder unklare Preise
  stoppen die Übernahme, statt einen Nullpreis zu erfinden.
- Einkaufspreis bleibt unbekannt/leer. Das Feld erlaubt nun NULL. Fehlendes
  Baujahr bleibt ebenfalls leer; bei zwei aktuellen Angeboten fehlt diese Angabe.
  Die Detailseite zeigt dafür „Keine Angabe“.
- Erneuter Import aktualisiert nur Felder, deren lokaler Wert noch dem letzten
  Importwert entspricht. Abweichende manuelle Werte bleiben erhalten; der Befehl
  meldet deren Anzahl. Einkaufspreis, Website-Freigabe, lokaler Verkaufsstatus und
  interne Nummer werden bei Wiederholungen nicht überschrieben.
- Die letzte API-Zuordnung wird gespeichert. Manuelle Werte, die exakt dem letzten
  API-Wert entsprechen, sind technisch nicht von unveränderten Werten unterscheidbar.

### Bilder und Fehlerverhalten

- Bilddownloads ausschließlich von `https://cdn.webmobil24.com/images/` über
  Standard-HTTPS-Port; keine Weiterleitungen und kein Authorization-Header am CDN.
- Maximal 100 Bilder pro Fahrzeug, 10 MiB pro Quelldatei, 40 Millionen Pixel.
  Nur JPEG/PNG/WebP; Bilddaten werden dekodiert und als WebP mit maximal
  1600 × 1200 Pixeln gespeichert. API-Antworten bleiben auf 8 MiB begrenzt.
- Externe Bild-ID und Version verhindern erneute Downloads unveränderter Bilder.
  Fehlende lokale Dateien werden repariert. Bestehende Hauptbildauswahl,
  Reihenfolge und Bildbeschreibungen bleiben bei Aktualisierungen erhalten.
- Lokal vorhandene Bilder werden nicht automatisch gelöscht, auch wenn sie nicht
  mehr in der API erscheinen. Alte ersetzte Bilddateien bleiben als Reserve erhalten.
- Erst wird der vollständige aktive Bestand mit allen Detaildaten geprüft, dann
  wird gespeichert. Ein fehlerhafter Datensatz stoppt die Prüfung vor dem Import.
- Downloads erfolgen pro Fahrzeug vor dessen Datenbanktransaktion. Ein Fehler
  lässt dieses Fahrzeug unverändert; vorher erfolgreich importierte Fahrzeuge
  bleiben erhalten. Wiederholung setzt ohne Duplikate fort. Kein globaler Rollback.
- Das aktive Bestandslisting ist auf 1000 Fahrzeuge begrenzt; unvollständige oder
  widersprüchliche Pagination wird abgewiesen. Keine automatischen Retries bei 429.

### Betrieb und Umfang

Vor den Migrationen und dem Erstimport wurde eine SQLite-Sicherung unter
`backups/before-wm24-import-20261012-151214.sqlite3` angelegt. `backups/` und
`backend/media/` sind von Git ausgeschlossen. Die Migrationen 0016/0017 der App
`vehicles` und 0001 der App `webmobil24_integration` wurden lokal ausgeführt.

Der Erstimport und erneute manuelle Import sind implementiert. Es gibt noch
keinen zeitgesteuerten Hintergrundabgleich und kein automatisches Ausblenden
verschwundener Angebote. Vor einer solchen Erweiterung müssen Verkaufssichtbarkeit
und Fehlerbehandlung beim Bestandsabgleich ausdrücklich festgelegt werden.

### Verifiziertes Ergebnis

- Erstimport: 28 unveröffentlichte Fahrzeuge und 1.068 Bilder erfolgreich gespeichert.
- Endbestand: 31 lokale Fahrzeuge einschließlich der drei bisherigen Angebote.
- Wiederholungsimport: 0 neue Fahrzeuge, 28 abgeglichene Fahrzeuge, 0 Bilddownloads.
- Alle 1.068 WebP-Dateien sind vorhanden und mit Pillow überprüft.
- Ursprüngliche Fahrzeugdaten und zugehörige Bilddatensätze stimmen unverändert
  mit der Sicherung überein (Vergleich nach Spaltennamen trotz geänderter SQLite-Spaltenreihenfolge).
- Geschützte Vorschau und Verwaltung liefern HTTP 200; öffentliche Detailseite
  eines Entwurfs liefert HTTP 404. Keine importierten Angebote öffentlich sichtbar.
- 159 Django-Tests bestanden, einschließlich 14 Import-/Vorschau-/Bildtests.
- Django-Systemcheck und `makemigrations --check --dry-run` ohne Befund;
  `git diff --check` sauber.

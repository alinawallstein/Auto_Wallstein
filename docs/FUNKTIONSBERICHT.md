# Funktionsbericht – Webseite Auto Wallstein

Stand: 10. Oktober 2026

Dieser Bericht beschreibt den im aktuellen Projektcode vorhandenen Funktionsumfang. Grundlage sind die aktive Django-Anwendung, ihre Seiten, Verwaltungsansichten und Verarbeitungsabläufe. Eine Prüfung der öffentlich betriebenen Webseite, des echten Mailversands oder der aktuellen Serverkonfiguration wurde für diesen Bericht nicht durchgeführt. Die archivierten Prototypen unter `legacy/` sind nicht Bestandteil dieser Bestandsaufnahme.

## 1. Öffentliche Webseite

### Startseite und Unternehmensdarstellung

- Startseite mit animiertem Logo, Bildslider, Begrüßung, Themenkacheln und Verweisen auf Fahrzeuge, Service und Finanzierung.
- Anzeige von bis zu sechs freigegebenen internen Fahrzeugangeboten und bis zu drei aktuellen Beiträgen.
- Einbindung eines externen Fahrzeugbestands von `auto-wallstein.qualitaetshaendler.de`.
- Kontaktinformationen, Öffnungszeiten, eingebettete Google-Karte und Link zur Routenplanung.
- Eigene Seiten für Über uns, Service und Zulassung, Finanzierung, Kontakt, Öffnungszeiten, Impressum und Datenschutz.
- Darstellung für Desktop und Smartphone mit aufklappbarer Navigation.

### Fahrzeuge suchen und ansehen

- Fahrzeugübersicht mit Preis, Bild und wesentlichen Fahrzeugdaten.
- Filter nach Marke, Modell, Preisbereich, Baujahrbereich, maximalem Kilometerstand, Kraftstoff und Getriebe.
- Sortierung nach neuesten Angeboten, Preis aufsteigend, Preis absteigend oder Kilometerstand.
- Anzeige der Trefferzahl sowie Rückmeldung bei fehlenden Treffern oder ungültigen Filterangaben.
- Fahrzeugdetailseiten mit Bildergalerie, anklickbaren Vorschaubildern und Öffnen der Bilder in voller Größe.
- Technische Daten, Beschreibung und Ausstattung, beispielsweise Erstzulassung, Leistung, Hubraum, Türen, Sitzplätze und Farbe.
- Direkte Fahrzeug- und Probefahrtanfragen mit vorausgewähltem Fahrzeug im Kontaktformular.
- Öffentlich erscheinen ausschließlich freigegebene, sichtbar geschaltete Fahrzeuge mit Status „Verfügbar“.

### Finanzierungsrechner

- Unverbindliche Berechnung auf der Finanzierungsseite anhand von Fahrzeugpreis, Anzahlung und Laufzeit.
- Anzeige von Finanzierungsbetrag, Monatsrate, Gesamtbetrag der Raten und Gesamtzinsen.
- Sofortige Neuberechnung bei Änderung der Eingaben.
- Prüfung der Eingaben, unter anderem auf eine zu hohe Anzahlung und eine Laufzeit außerhalb von 1 bis 120 Monaten.
- Zentral in der Verwaltung einstellbarer effektiver Jahreszins. Ohne hinterlegte Konditionen erfolgt keine Berechnung.

Der Rechner erstellt ein Rechenbeispiel. Eine Bankanbindung, Bonitätsprüfung oder verbindliche Kreditzusage ist im geprüften Ablauf nicht vorhanden. Der angezeigte Gesamtbetrag umfasst die Kreditraten; die Anzahlung kommt zum gesamten Kaufaufwand hinzu.

### Kontakt und automatische E-Mails

- Kontaktformular für Fahrzeug-, Probefahrt- und Finanzierungsanfragen.
- Erfassung von Name, E-Mail-Adresse, optionaler Telefonnummer, Nachricht und optionalem Fahrzeugbezug.
- Dauerhafte Speicherung der Anfrage in der Datenbank.
- Versand einer Benachrichtigung an die konfigurierte Händleradresse und einer Empfangsbestätigung an den Kunden.
- Empfangsbestätigung als HTML-E-Mail mit zusätzlicher Textfassung; bei Fahrzeugbezug mit Fahrzeuginformationen und automatisch erzeugtem PDF-Exposé als Anhang.
- Das Exposé enthält Angebot, Fahrzeugdaten, Beschreibung, Ausstattung und vorhandene Fahrzeugbilder.
- Gespeicherte Anfragen bleiben auch bei einem Mailfehler erhalten.

Der tatsächliche Versand setzt eine funktionierende Mailkonfiguration voraus. Eine erfolgreiche Übergabe an den Mailserver bestätigt noch nicht die Zustellung beim Empfänger.

### Teile und Zubehör

- Öffentliche Angebotsübersicht unter `/zubehoer/` mit Seitenaufteilung.
- Detailseiten mit Bildern, Beschreibung, Preis, Zustand und Angaben zur Kompatibilität.
- Kategorien für Reifen, Felgen und Kompletträder, Autoteile und sonstiges Zubehör.
- Nur veröffentlichte, verfügbare Angebote sind öffentlich sichtbar.
- Kontaktaufnahme per Telefon oder E-Mail; keine Warenkorb-, Zahlungs- oder Bestellabwicklung.

### Aktuelles und Neuigkeiten

- Öffentliche Beitragsübersicht unter `/aktuelles/` und eigene Detailseiten mit lesbaren URL-Adressen.
- Beiträge für Neuigkeiten, neue Fahrzeuge, Aktionen, Unternehmen, Veranstaltungen und Hinweise.
- Filter für die speziellen Beitragskategorien, Seitenaufteilung und hervorgehobene Beiträge.
- Veranstaltungsinformationen mit Datum, Uhrzeit und Ort sowie Verknüpfung mit einem Fahrzeug.
- Zeitgesteuerte Sichtbarkeit anhand des Veröffentlichungsdatums und Ausblenden nach einem optionalen Gültigkeitsende.
- Entwürfe und archivierte Beiträge werden öffentlich nicht angezeigt.

### Bedienhilfen

- Einstellbare Schriftgröße von 80 bis 140 Prozent, erhöhter Kontrast, hervorgehobene Links und reduzierte Bewegung.
- Speicherung dieser Einstellungen im jeweiligen Browser und Möglichkeit zum Zurücksetzen.
- Tastaturbedienung, Bildbeschreibungen und zugängliche Rückmeldungen bei Formularfehlern.
- Rücksicht auf reduzierte Bewegung im Slider und Bedienung über Pfeile, Navigationspunkte und Wischgesten.

Diese Funktionen sind Bedienhilfen; daraus folgt keine geprüfte oder zertifizierte vollständige Barrierefreiheit.

## 2. Interne Verwaltung

### Anmeldung, Rechte und Dashboard

- Eigener Verwaltungsbereich unter `/verwaltung/` mit An- und Abmeldung.
- Zugriff abhängig von Benutzerrechten; nur erlaubte Bereiche werden angezeigt.
- Technischer Django-Admin unter `/admin/`, unter anderem zur Benutzer- und Gruppenverwaltung.
- Dashboard mit Fahrzeugbestand, verfügbaren und öffentlichen Fahrzeugen, Statusverteilung und Kraftstoffverteilung.
- Anfragekennzahlen für neue, offene und beantwortete Anfragen sowie neue Finanzierungsanfragen.
- Darstellung der Anfrageaktivität der vergangenen 30 Tage und zuletzt eingegangener Anfragen.
- Übersicht über aktuelle Fahrzeuge, Neuigkeiten, geplante Veröffentlichungen und aktive Slides.

### Fahrzeugbestand und Bilder

- Fahrzeuge anlegen, bearbeiten und nach Bestätigung löschen.
- Verwaltung von Stammdaten, technischen Daten, Ausstattung und Beschreibung.
- Interne Angaben wie Fahrzeugnummer, FIN, Einkaufspreis, Vorbesitzer und HU-Gültigkeit.
- Verkaufsstatus und Website-Freigabe getrennt verwalten.
- Bestandsliste mit Suche, Status- und Sichtbarkeitsfiltern sowie Seitenaufteilung.
- Mehrere Fahrzeugbilder hochladen, Hauptbild auswählen, Reihenfolge ändern, Bildbeschreibungen pflegen und Bilder löschen.

### Kundenanfragen bearbeiten

- Anfrageübersicht mit Suche, Statusfilter, Datumsortierung und Seitenaufteilung.
- Detailansicht mit Originalnachricht, Kontaktdaten und Fahrzeugbezug.
- Statuswerte: Neu, Gelesen, In Bearbeitung, Beantwortet und Erledigt.
- Neue Anfragen werden beim Öffnen durch Mitarbeiter mit Änderungsrecht als gelesen markiert.
- Direkte Antworten per E-Mail aus der Verwaltung.
- Antwortverlauf mit Text, Mitarbeiter, Empfänger, Betreff, Zeitstempel und Versandstatus.
- Schutz vor doppeltem Versand desselben Antwortformulars; Fehler und Testversand bleiben im Verlauf erkennbar.
- Nach erfolgreicher Übergabe einer echten Antwort an das Mailbackend wird die Anfrage als beantwortet markiert.

Der Verlauf erfasst ausgehende Antworten. Eingehende Antworten aus einem externen E-Mail-Postfach werden nicht synchronisiert.

### Startseite und Slider pflegen

- Vorhandene Startseitentexte, Bildkacheln, Kontaktdaten und Öffnungszeiten bearbeiten.
- Inhalte zunächst als Entwurf speichern, geschützt ansehen und anschließend veröffentlichen.
- Schutz gegen Überschreiben durch veraltete Bearbeitungsstände.
- Veröffentlichte Kontaktdaten werden an mehreren Stellen der Webseite verwendet.
- Bildslider mit Bildern, optionalen Überschriften, Untertiteln und verlinkten Buttons verwalten.
- Slides anlegen, bearbeiten, sortieren, aktivieren, deaktivieren und löschen.
- Getrennte Bildausschnitte für Desktop und Smartphone mit Vorschau sowie Anpassung von Bildgröße und Position.
- Automatische Erzeugung der Sliderbilder im WebP-Format.
- Einstellbare Wechselzeit zwischen 2 und 15 Sekunden.
- Aktive Slides werden sofort nach dem Speichern öffentlich; für Website-Texte gilt der separate Veröffentlichungsablauf.

### Zubehör und Beiträge pflegen

- Zubehörangebote mit Preis, Kategorie, Zustand, Verkaufsstatus und bis zu zwölf Bildern anlegen und bearbeiten.
- Hauptbild über die Bildreihenfolge bestimmen und Angebote in einer geschützten Vorschau prüfen.
- Beiträge mit Überschrift, Kurztext, Inhalt, Titelbild und Bildbeschreibung erstellen und bearbeiten.
- Entwürfe, Veröffentlichung, Archivierung, Hervorhebung und Veröffentlichungsdatum verwalten.
- Gültigkeitsende, Veranstaltungsdaten und Fahrzeugverknüpfung pflegen.
- Interne Beitragssuche und Filter nach Typ, Status und Veröffentlichungszeitraum.

## 3. Vorbereitete Funktionen und Grenzen

- Datenstrukturen für gespeicherte KI-Texte zu Fahrzeugen sind vorhanden und über den technischen Admin pflegbar. Eine automatische KI-Texterzeugung ist daraus nicht nachgewiesen.
- Technische Bausteine für gespeicherte Finanzierungskonditionen an Anfragen sind vorhanden. Das aktuelle öffentliche Kontaktformular überträgt jedoch keine Berechnungswerte aus dem Finanzierungsrechner; auf der Fahrzeugdetailseite ist kein eigener Rechner eingebunden.
- Der externe Fahrzeugbestand wird eingebettet. Ein automatischer Import oder Abgleich mit den intern gepflegten Fahrzeugen ist im geprüften Ablauf nicht vorhanden.
- Die Informationsseiten für Service und Zulassung bieten keine automatische Terminbuchung oder Zulassungsabwicklung.
- Impressum und Datenschutz sind vorhanden; ihre rechtliche Aktualität wurde in dieser Bestandsaufnahme nicht geprüft.

## 4. Grundlage der Bestandsaufnahme

Geprüft wurden insbesondere die öffentlichen und internen Routen, Views, Modelle, Formulare, Templates, Dashboard-Abfragen, Mailabläufe, PDF-Erzeugung und JavaScript-Bedienhilfen. Projektunterlagen wurden ergänzend verwendet; bei abweichenden älteren Angaben ist der aktuelle Code maßgeblich. Es wurden keine Inhalte geändert, Kunden angeschrieben oder neuen Funktionstests ausgeführt.

Wichtige Quellbereiche:

- `backend/vehicles/urls.py` und `urls_management.py`: erreichbare Funktionen und Seiten.
- `backend/vehicles/views.py`, `catalog_views.py`, `content_views.py`, `slider_views.py`, `inquiry_views.py` und `management.py`: öffentliche und interne Abläufe.
- `backend/templates/public/`: tatsächlich eingebundene öffentliche Seitenfunktionen.
- `backend/vehicles/inquiry_mail.py` und `expose_pdf.py`: Kundenkommunikation und Exposé.
- `backend/static/js/`: Slider, Bildergalerie, Navigation, Bedienhilfen und Formularunterstützung.

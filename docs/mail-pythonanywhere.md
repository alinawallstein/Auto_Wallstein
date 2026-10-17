# Microsoft-365-Mail auf PythonAnywhere

Stand: 17.10.2026. DNS: MX `autowallstein-de01b.mail.protection.outlook.com`,
Autodiscover `autodiscover.outlook.com`, SPF Microsoft 365. Nutzer bestätigt Outlook
im Web und einen kostenpflichtigen PythonAnywhere-Tarif.

Der Graph-Transport ist vorbereitet, aber nicht automatisch aktiviert. Vorhandene
Kontaktbenachrichtigungen, HTML-Bestätigungen mit PDF und Verwaltungsantworten
verwenden denselben Django-Transport. Lokale Tests simulieren Microsoft;
Authentifizierung und Zustellung auf dem Server sind noch nicht geprüft.

## 1. Microsoft-Administrator: Anwendung anlegen

In https://entra.microsoft.com unter Identität → Anwendungen → App-Registrierungen
eine Anwendung „Auto Wallstein Website Mail“ anlegen. Nur Konten dieses Mandanten
wählen; keine Umleitungsadresse nötig. Mandanten-ID und Anwendungs-/Client-ID
für die Serverkonfiguration notieren.

Unter Zertifikate & Geheimnisse ein zeitlich begrenztes Clientgeheimnis erstellen.
Den **Wert** direkt in die private Datei auf PythonAnywhere übertragen, niemals in
Chat, GitHub, Screenshots oder Shellbefehle. Ablaufdatum vormerken und rechtzeitig
rotieren. Dieses Geheimnis ist ein Anwendungszugang, kein Outlook-Passwort.

Unter Unternehmensanwendungen dieselbe Anwendung öffnen und deren Objekt-ID
notieren. Die Objekt-ID der App-Registrierung ist hierfür falsch.

## 2. Administrator: Versand auf das Verkaufspostfach begrenzen

Ein Exchange-Administrator führt in Exchange Online PowerShell aus.
Platzhalter ersetzen; vorher prüfen, dass verkauf@auto-wallstein.de ein Postfach
und dessen primäre Adresse ist (nicht lediglich Verteiler oder Weiterleitung).

```powershell
Connect-ExchangeOnline
Get-EXOMailbox -Identity verkauf@auto-wallstein.de
New-ServicePrincipal -AppId <CLIENT-ID> -ObjectId <OBJEKT-ID-DER-UNTERNEHMENSANWENDUNG> -DisplayName "Auto Wallstein Website Mail"
New-ManagementScope -Name "Wallstein-Verkauf-Mail" -RecipientRestrictionFilter "PrimarySmtpAddress -eq 'verkauf@auto-wallstein.de'"
New-ManagementRoleAssignment -Name "Wallstein-Website-Senden" -Role "Application Mail.Send" -App <OBJEKT-ID-DER-UNTERNEHMENSANWENDUNG> -CustomResourceScope "Wallstein-Verkauf-Mail"
Test-ServicePrincipalAuthorization -Identity <OBJEKT-ID-DER-UNTERNEHMENSANWENDUNG> -Resource verkauf@auto-wallstein.de
```

Für `Application Mail.Send` muss `InScope` wahr sein. Zusätzlich ein anderes
vorhandenes Postfach prüfen: dort muss `InScope` falsch sein. Diese Prüfungen
senden keine Mail. Änderungen können 30 Minuten bis zwei Stunden benötigen.

Für diesen RBAC-Weg **keine zusätzliche mandantenweite Graph-Mail.Send-
Anwendungsberechtigung in Entra gewähren**: Berechtigungen addieren sich und
könnten die Begrenzung umgehen. Bestehende unbeschränkte Grants muss der
Administrator prüfen. SMTP AUTH braucht für Graph nicht aktiviert zu werden.

## 3. PythonAnywhere: Geheimnisse außerhalb des Git-Projekts speichern

In einer Bash-Konsole (Benutzernamen/Pfade entsprechend anpassen):

```bash
mkdir -p ~/.config/auto-wallstein
chmod 700 ~/.config/auto-wallstein
umask 077
touch ~/.config/auto-wallstein/mail.env
chmod 600 ~/.config/auto-wallstein/mail.env
nano ~/.config/auto-wallstein/mail.env
```

In diese private Datei kommen folgende Werte; Geheimnis nur dort einfügen:

```dotenv
EMAIL_BACKEND=vehicles.graph_mail.EmailBackend
DEFAULT_FROM_EMAIL=verkauf@auto-wallstein.de
INQUIRY_NOTIFICATION_EMAIL=verkauf@auto-wallstein.de
MS_GRAPH_MAILBOX=verkauf@auto-wallstein.de
MS_GRAPH_TENANT_ID=<MANDANTEN-ID>
MS_GRAPH_CLIENT_ID=<CLIENT-ID>
MS_GRAPH_CLIENT_SECRET='<GEHEIMNISWERT>'
EMAIL_TIMEOUT=15
```

Datei nicht herunterladen, committen oder ins Projekt kopieren. Die vorhandene
Projekt-`.env` darf keine widersprechenden Mailwerte enthalten: Bereits gesetzte
Umgebungswerte haben Vorrang. Keine Konfiguration mit `env` oder `print(settings)`
in Logs ausgeben.

Den neuen Code auf PythonAnywhere bereitstellen. Im Web-Tab die dort verlinkte
WSGI-Konfigurationsdatei öffnen und **vor** `get_wsgi_application()` ergänzen:

```python
os.environ['MAIL_ENV_FILE'] = '/home/DEIN_BENUTZERNAME/.config/auto-wallstein/mail.env'
```

Noch nicht neu laden: Erst Authentifizierung ohne Versand prüfen.

## 4. Ohne Mailversand prüfen

In der Bash-Konsole dieselbe virtuelle Umgebung wie die Web-App aktivieren,
in das Verzeichnis mit manage.py wechseln und ausführen:

```bash
export MAIL_ENV_FILE="$HOME/.config/auto-wallstein/mail.env"
python manage.py check
python manage.py check_mail_auth
```

Der zweite Befehl holt nur ein OAuth-Token in den Arbeitsspeicher. Er sendet keine
Mail und zeigt kein Token. Er funktioniert auch bei noch nicht aktiviertem
Graph-Mailbackend. Erfolg beweist noch keine Postfachberechtigung oder
Zustellung. Fehler nur als bereinigte Meldung weitergeben, niemals Dateiinhalte.

## 5. Erst nach ausdrücklicher Zustimmung testen und aktivieren

Empfänger und Testumfang vorher abstimmen. Dann Web-App neu laden und eine
kontrollierte Kontaktanfrage stellen. Achtung: Schon diese Anfrage versendet
Benachrichtigung UND Kundenbestätigung. Anschließend eine Verwaltungsantwort
an den vereinbarten Testempfänger senden. Bei Fahrzeuganfragen auch HTML und
PDF-Anhang prüfen. Eingang/Spam und Microsoft „Gesendete Elemente“ kontrollieren.
Bei Problemen Exchange-Nachrichtenablaufverfolgung nutzen.

Erst tatsächlichen Eingang aller drei Mailarten als funktionierend melden.
Graph `202 Accepted` und Verwaltungsstatus „gesendet“ bedeuten Transportannahme,
keinen Zustellnachweis. Anfragen bleiben bei Versandfehlern gespeichert;
fehlgeschlagene Benachrichtigungen/Bestätigungen werden derzeit nicht automatisch
wiederholt. Vor Aktivierung können bestehende Anfragen ebenfalls echte Mails
auslösen; daher die Aktivierung mit dem Versandtest abstimmen.

## Bereits vorhandene backend/.env

In dieser Einrichtung verwendet der Nutzer seine bestehende `backend/.env`.
Sie wird bereits durch Django geladen. `git ls-files -- .env` wurde auf dem
Server ohne Ausgabe geprüft und `chmod 600 .env` ausgeführt. Die Graph-Werte
können dort bleiben; `MAIL_ENV_FILE` und eine zweite Datei sind dann unnötig.
Die Datei niemals mit `git add -f` aufnehmen oder über GitHub übertragen.
`EMAIL_BACKEND=vehicles.graph_mail.EmailBackend` erst zur abgestimmten
Aktivierung setzen. Der Authentifizierungscheck braucht diese Einstellung nicht.

## Quellen

- [Microsoft Graph sendMail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0)
- [OAuth2 Client Credentials](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow)
- [Exchange Application RBAC](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac)

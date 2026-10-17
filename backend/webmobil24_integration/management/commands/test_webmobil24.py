"""Bounded, read-only API connection check, without database access."""
from django.core.management.base import BaseCommand, CommandError
from vehicles.webmobil24 import APIError, Client, Config


class Command(BaseCommand):
    help = "WebMobil24 nur lesend testen; keine Daten importieren."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--list-dealers", action="store_true")
        parser.add_argument("--environment", choices=["test", "production"])
        parser.add_argument("--page-size", type=int, default=10)
        parser.add_argument("--max-pages", type=int, default=1)

    def handle(self, *args, **options):
        if not 1 <= options["page_size"] <= 100 or not 1 <= options["max_pages"] <= 10:
            raise CommandError("Lokale Grenzen: page-size 1–100, max-pages 1–10.")
        try:
            client = Client(Config.from_env(options["environment"]))
            self.stdout.write(f"Umgebung: {client.config.environment}; ausschließlich GET.")
            discovery = options["list_dealers"]
            fetch = client.dealers if discovery else client.listings
            seen, first, offset, total, complete = set(), None, 0, None, False
            for _ in range(options["max_pages"]):
                page = fetch(offset=offset, limit=options["page_size"])
                total = page.total
                for item in page.items:
                    identifier = item["dealerId" if discovery else "listingId"]
                    if identifier in seen:
                        raise APIError("Pagination liefert bereits abgerufene IDs.")
                    seen.add(identifier)
                    if first is None:
                        first = item
                    if discovery:
                        # Never print whole dealer records (may contain export credentials).
                        company = str(item.get("company", ""))
                        company = "".join(c for c in company if c.isprintable())[:120]
                        company = company.replace(client.config.token, "[redacted]")
                        self.stdout.write(f"Händler-ID: {identifier}; Firma: {company}")
                offset += len(page.items)
                if len(page.items) < options["page_size"] or (total is not None and offset >= total):
                    complete = True
                    break
            self.stdout.write(f"Authentifizierung/Abruf OK; {len(seen)} Datensätze geprüft; "
                              f"Gesamtzahl: {total if total is not None else 'unbekannt'}; "
                              f"{'Abruf vollständig' if complete else 'lokales Seitenlimit erreicht'}.")
            if not discovery:
                if first is None:
                    self.stdout.write("Keine aktiven Fahrzeuge; Detail-/Bildprüfung übersprungen.")
                else:
                    client.detail(first["listingId"])
                    images = client.images(first["listingId"])
                    self.stdout.write(f"Fahrzeugdetails OK; {len(images)} HTTPS-Bildadressen validiert (kein Download).")
        except APIError as exc:
            raise CommandError(str(exc)) from None

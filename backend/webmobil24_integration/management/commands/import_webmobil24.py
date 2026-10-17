"""Validate the complete Webmobil24 inventory before applying imports."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from vehicles.models import Vehicle
from vehicles.webmobil24 import APIError, Client, Config, positive_id
from webmobil24_integration.importer import import_listing, mapping
from webmobil24_integration.models import ImportedListing


PAGE_SIZE = 100
MAX_PAGES = 10


def fetch_listings(client):
    """Read a bounded, complete inventory and reject inconsistent pages."""
    listings, seen, expected = [], set(), None
    for _ in range(MAX_PAGES):
        page = client.listings(offset=len(listings), limit=PAGE_SIZE)
        if expected is not None and page.total != expected:
            raise APIError("Bestand während Pagination verändert; erneut versuchen.")
        expected = page.total
        for item in page.items:
            identifier = positive_id(item["listingId"])
            if identifier in seen:
                raise APIError("Doppelte Fahrzeug-ID in Pagination.")
            seen.add(identifier)
            listings.append(item)
        if (expected is not None and len(listings) == expected) or len(page.items) < PAGE_SIZE:
            if expected is not None and len(listings) != expected:
                raise APIError("Bestand unvollständig.")
            return listings
    raise APIError(f"Lokales Limit von {PAGE_SIZE * MAX_PAGES} Fahrzeugen erreicht.")


def validate_vehicle(client, data, mapped):
    """Check model constraints without persisting the candidate vehicle."""
    source = ImportedListing.objects.select_related("vehicle").filter(
        environment=client.config.environment,
        dealer_id=client.config.dealer_id,
        listing_id=data["listingId"],
    ).first()
    if source:
        candidate = source.vehicle
        for key, value in mapped.items():
            setattr(candidate, key, value)
    else:
        candidate = Vehicle(
            **mapped,
            purchase_price=None,
            internal_number=(
                f"WM24-{client.config.environment}-"
                f"{client.config.dealer_id}-{data['listingId']}"
            ),
        )
    try:
        candidate.full_clean()
    except ValidationError:
        raise APIError(
            f"Fahrzeug {data['listingId']}: Daten passen nicht zu den lokalen Feldern."
        ) from None


def prepare_import(client):
    """Validate all detail records before the first database or image write."""
    equipment, _ = client._get("/references/equipment", {"language": "DE"})
    if not isinstance(equipment, dict):
        raise APIError("Ungültige Ausstattungsreferenzen.")
    plans = []
    for listing in fetch_listings(client):
        data = client.detail(listing["listingId"])
        mapped = mapping(data, equipment)
        validate_vehicle(client, data, mapped)
        plans.append((data, mapped, client.images(listing["listingId"])))
    return plans


class Command(BaseCommand):
    help = "Webmobil24 als lokale Entwürfe importieren; standardmäßig nur Vorschau."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Lokal speichern und Bilder herunterladen.",
        )

    def handle(self, *args, **options):
        try:
            client = Client(Config.from_env())
            plans = prepare_import(client)
            apply = options["apply"]
            mode = "Import" if apply else "Vorschau ohne Änderungen"
            self.stdout.write(f"{len(plans)} Fahrzeuge geprüft; Modus: {mode}.")
            created_count = image_count = 0
            for data, mapped, images in plans:
                if apply:
                    created, downloaded, conflicts = import_listing(client, data, mapped, images)
                    created_count += int(created)
                    image_count += downloaded
                    state = "neu" if created else "abgeglichen"
                    self.stdout.write(
                        f"Fahrzeug {data['listingId']}: {state}; {downloaded} Bilder geladen; "
                        f"{len(conflicts)} manuelle Felder erhalten."
                    )
                else:
                    self.stdout.write(
                        f"Fahrzeug {data['listingId']}: {len(images)} Bilder; Daten gültig."
                    )
                self.stdout.flush()
            if apply:
                self.stdout.write(self.style.SUCCESS(
                    f"Fertig: {created_count} neue Entwürfe, "
                    f"{len(plans) - created_count} bestehende Fahrzeuge abgeglichen, "
                    f"{image_count} Bilder geladen. Keine automatische Veröffentlichung."
                ))
        except APIError as exc:
            raise CommandError(str(exc)) from None

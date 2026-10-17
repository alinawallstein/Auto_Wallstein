from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from vehicles.models import Vehicle
from vehicles.webmobil24 import APIError, Client, Config, positive_id
from webmobil24_integration.importer import mapping, import_listing
from webmobil24_integration.models import ImportedListing


class Command(BaseCommand):
    help = 'Webmobil24 als lokale Entwürfe importieren; standardmäßig nur Vorschau.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Lokal speichern und Bilder herunterladen.')

    def handle(self, *args, **options):
        try:
            client = Client(Config.from_env())
            equipment, _ = client._get('/references/equipment', {'language': 'DE'})
            if not isinstance(equipment, dict):
                raise APIError('Ungültige Ausstattungsreferenzen.')
            listings, seen, expected = [], set(), None
            for page_number in range(10):
                page = client.listings(offset=len(listings), limit=100)
                if expected is not None and page.total != expected:
                    raise APIError('Bestand während Pagination verändert; erneut versuchen.')
                expected = page.total
                for item in page.items:
                    identifier = positive_id(item['listingId'])
                    if identifier in seen:
                        raise APIError('Doppelte Fahrzeug-ID in Pagination.')
                    seen.add(identifier)
                    listings.append(item)
                if (expected is not None and len(listings) == expected) or len(page.items) < 100:
                    if expected is not None and len(listings) != expected:
                        raise APIError('Bestand unvollständig.')
                    break
            else:
                raise APIError('Lokales Limit von 1000 Fahrzeugen erreicht.')
            # Validate all detail records before the first write.
            plans = []
            for listing in listings:
                data = client.detail(listing['listingId'])
                mapped = mapping(data, equipment)
                source = ImportedListing.objects.filter(environment=client.config.environment,
                    dealer_id=client.config.dealer_id, listing_id=data['listingId']).first()
                candidate = Vehicle(**mapped, purchase_price=None,
                    internal_number=f'WM24-{client.config.environment}-{client.config.dealer_id}-{data["listingId"]}')
                if source:
                    candidate = source.vehicle
                    for key, value in mapped.items():
                        setattr(candidate, key, value)
                try:
                    candidate.full_clean()
                except ValidationError:
                    raise APIError(f'Fahrzeug {data["listingId"]}: Daten passen nicht zu den lokalen Feldern.') from None
                plans.append((data, mapped, client.images(listing['listingId'])))
            self.stdout.write(f'{len(plans)} Fahrzeuge geprüft; Modus: {"Import" if options["apply"] else "Vorschau ohne Änderungen"}.')
            created_count = image_count = 0
            for data, mapped, images in plans:
                if options['apply']:
                    created, downloaded, conflicts = import_listing(client, data, mapped, images)
                    created_count += int(created)
                    image_count += downloaded
                    self.stdout.write(f'Fahrzeug {data["listingId"]}: {"neu" if created else "abgeglichen"}; {downloaded} Bilder geladen; {len(conflicts)} manuelle Felder erhalten.')
                else:
                    self.stdout.write(f'Fahrzeug {data["listingId"]}: {len(images)} Bilder; Daten gültig.')
                self.stdout.flush()
            if options['apply']:
                self.stdout.write(self.style.SUCCESS(f'Fertig: {created_count} neue Entwürfe, {len(plans)-created_count} bestehende Fahrzeuge abgeglichen, {image_count} Bilder geladen. Keine automatische Veröffentlichung.'))
        except APIError as exc:
            raise CommandError(str(exc)) from None

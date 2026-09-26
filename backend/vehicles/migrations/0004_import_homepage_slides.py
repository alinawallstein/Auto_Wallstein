from django.db import migrations


def import_slides(apps, schema_editor):
    Homepage = apps.get_model('vehicles', 'Homepage')
    HomepageImage = apps.get_model('vehicles', 'HomepageImage')
    HeroSlide = apps.get_model('vehicles', 'HeroSlide')
    database = schema_editor.connection.alias
    page = Homepage.objects.using(database).filter(pk=1).first()
    if not page:
        return
    images = HomepageImage.objects.using(database).in_bulk()
    imported = set()
    for active, values in ((True, page.published), (False, page.draft)):
        for position, key in enumerate(('hero_image', 'hero_image_2', 'hero_image_3', 'hero_image_4', 'hero_image_5')):
            asset = images.get(values.get(key))
            if not asset or not asset.image or asset.image.name in imported:
                continue
            HeroSlide.objects.using(database).create(
                title=values.get('hero_title', 'Mercedes Benz Jahres-& Geschäftswagen')[:180],
                subtitle=values.get('hero_text', '')[:500],
                image=asset.image.name,
                button_text=values.get('hero_button', '')[:60],
                button_url='/fahrzeuge/' if values.get('hero_button') else '',
                sort_order=(position + 1) * 10,
                is_active=active,
            )
            imported.add(asset.image.name)
    # Keep the original JSON and files intact as an archive; the new editor no longer uses these keys.


class Migration(migrations.Migration):
    dependencies = [('vehicles', '0003_heroslide')]
    operations = [migrations.RunPython(import_slides, migrations.RunPython.noop)]

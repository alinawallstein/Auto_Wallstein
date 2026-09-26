from django.db import migrations


def snapshot_subjects(apps, schema_editor):
    Inquiry = apps.get_model('vehicles', 'CustomerInquiry')
    database = schema_editor.connection.alias
    labels = dict(Inquiry._meta.get_field('inquiry_type').choices)
    for inquiry in Inquiry.objects.using(database).filter(subject='').select_related('vehicle').iterator():
        vehicle = f'{inquiry.vehicle.brand} {inquiry.vehicle.model}' if inquiry.vehicle else ''
        subject = f'{labels.get(inquiry.inquiry_type, "Kundenanfrage")}{": " + vehicle if vehicle else ""}'
        Inquiry.objects.using(database).filter(pk=inquiry.pk).update(subject=subject[:300])


class Migration(migrations.Migration):
    dependencies = [('vehicles', '0005_inquiryreply_alter_homepage_options_and_more')]
    operations = [migrations.RunPython(snapshot_subjects, migrations.RunPython.noop)]

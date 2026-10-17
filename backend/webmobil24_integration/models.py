from django.db import models


class ImportedListing(models.Model):
    vehicle = models.OneToOneField('vehicles.Vehicle', on_delete=models.CASCADE, related_name='webmobil24_source')
    environment = models.CharField(max_length=10)
    dealer_id = models.PositiveIntegerField()
    listing_id = models.PositiveIntegerField()
    source_data = models.JSONField(default=dict)
    last_mapping = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['environment', 'dealer_id', 'listing_id'], name='wm24_listing_identity')]


class ImportedImage(models.Model):
    listing = models.ForeignKey(ImportedListing, on_delete=models.CASCADE, related_name='imported_images')
    image = models.OneToOneField('vehicles.VehicleImage', on_delete=models.CASCADE)
    remote_id = models.PositiveIntegerField()
    source_version = models.CharField(max_length=1000)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['listing', 'remote_id'], name='wm24_image_identity')]

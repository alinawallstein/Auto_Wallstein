from django.contrib import admin

from .models import CustomerInquiry, Vehicle, VehicleAIText, VehicleImage


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "internal_number",
        "brand",
        "model",
        "status",
        "is_published",
        "public_visible",
        "sale_price",
        "updated_at",
    )
    list_filter = ("status", "is_published", "public_visible", "brand")
    search_fields = ("internal_number", "brand", "model", "vin")
    inlines = [VehicleImageInline]


@admin.register(CustomerInquiry)
class CustomerInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "inquiry_type", "vehicle", "created_at")
    list_filter = ("inquiry_type", "created_at")
    search_fields = ("name", "email", "vehicle__brand", "vehicle__model")


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "is_main", "sort_order")


@admin.register(VehicleAIText)
class VehicleAITextAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "text_type", "created_at")

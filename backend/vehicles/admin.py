from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .catalog_forms import validate_photo
from .models import CustomerInquiry, HeroSlide, Vehicle, VehicleAIText, VehicleImage


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


class HeroSlideAdminForm(forms.ModelForm):
    image = forms.ImageField(label='Bild', validators=[validate_photo],
                             help_text='JPEG, PNG oder WebP, höchstens 10 MB. Querformat empfohlen.')

    class Meta:
        model = HeroSlide
        fields = '__all__'
        widgets = {'subtitle': forms.Textarea(attrs={'rows': 3})}


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    form = HeroSlideAdminForm
    list_display = ('__str__', 'image_preview', 'sort_order', 'is_active', 'updated_at')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle', 'image_alt')
    ordering = ('sort_order', 'pk')
    readonly_fields = ('image_preview', 'created_at', 'updated_at')
    fieldsets = (
        ('Inhalt', {'fields': ('title', 'subtitle', 'image', 'image_alt', 'image_preview')}),
        ('Optionaler Button', {'fields': ('button_text', 'button_url')}),
        ('Veröffentlichung', {'fields': ('sort_order', 'is_active')}),
        ('Zeitstempel', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Bildvorschau')
    def image_preview(self, obj):
        if not obj.image:
            return 'Kein Bild'
        return format_html('<img class="hero-admin-preview" src="{}" alt="{}" width="144" height="90">',
                           obj.image.url, obj.image_alt)

    class Media:
        css = {'all': ('css/hero-admin.css',)}

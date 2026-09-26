from django.contrib import admin
from django.utils.html import format_html

from .slider_forms import HeroSlideForm
from .models import CustomerInquiry, HeroSlide, InquiryReply, NewsArticle, Vehicle, VehicleAIText, VehicleImage


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'status', 'published_at', 'is_featured')
    list_filter = ('type', 'status', 'is_featured', 'published_at')
    search_fields = ('title', 'excerpt', 'body')
    date_hierarchy = 'published_at'
    exclude = ('slug',)


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
    list_display = ("name", "email", "inquiry_type", "vehicle", "status", "created_at")
    list_filter = ("status", "inquiry_type", "created_at")
    readonly_fields = ("name", "email", "phone", "message", "inquiry_type", "subject", "vehicle", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    search_fields = ("name", "email", "vehicle__brand", "vehicle__model")


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "is_main", "sort_order")


@admin.register(VehicleAIText)
class VehicleAITextAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "text_type", "created_at")


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    form = HeroSlideForm
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


@admin.register(InquiryReply)
class InquiryReplyAdmin(admin.ModelAdmin):
    list_display = ('inquiry', 'recipient', 'status', 'created_at', 'sent_at', 'author')
    list_filter = ('status',)
    search_fields = ('recipient', 'subject')
    readonly_fields = ('inquiry', 'body', 'recipient', 'subject', 'status', 'request_id', 'author', 'created_at', 'sent_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

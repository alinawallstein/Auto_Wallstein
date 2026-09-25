from __future__ import annotations

from django import forms

from .models import CustomerInquiry, Vehicle, VehicleAIText, VehicleImage, VehicleStatus


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "internal_number",
            "brand",
            "model",
            "variant",
            "vehicle_type",
            "first_registration",
            "year",
            "mileage",
            "fuel_type",
            "transmission",
            "power_kw",
            "power_ps",
            "engine_capacity",
            "doors",
            "seats",
            "exterior_color",
            "interior_equipment",
            "vin",
            "previous_owners",
            "hu_valid_until",
            "purchase_price",
            "sale_price",
            "description",
            "equipment",
            "status",
            "is_published",
            "public_visible",
        ]
        widgets = {
            "first_registration": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "hu_valid_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "equipment": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get("class", "")
            if field_name not in {"first_registration", "hu_valid_until", "description", "equipment", "status"}:
                field.widget.attrs["class"] = f"{existing_classes} form-control".strip()
            if field_name == "is_published" or field_name == "public_visible":
                field.widget.attrs["class"] = "form-check-input"

    def clean(self):
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get("purchase_price")
        sale_price = cleaned_data.get("sale_price")

        if purchase_price is not None and purchase_price < 0:
            self.add_error("purchase_price", "Der Einkaufspreis darf nicht negativ sein.")
        if sale_price is not None and sale_price < 0:
            self.add_error("sale_price", "Der Verkaufspreis darf nicht negativ sein.")
        if sale_price is not None and purchase_price is not None and sale_price < 0:
            self.add_error("sale_price", "Der Verkaufspreis darf nicht kleiner als 0 sein.")

        if cleaned_data.get("status") == VehicleStatus.SOLD and not cleaned_data.get("is_published"):
            cleaned_data["is_published"] = False

        return cleaned_data


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VehicleImageUploadForm(forms.Form):
    images = forms.FileField(
        widget=MultipleFileInput(attrs={"multiple": True, "class": "form-control"}),
        required=True,
        label="Bilder hochladen",
    )


class VehicleImageActionForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput())
    image_id = forms.IntegerField(widget=forms.HiddenInput())


class CustomerInquiryForm(forms.ModelForm):
    class Meta:
        model = CustomerInquiry
        fields = ["inquiry_type", "vehicle", "name", "email", "phone", "message"]
        widgets = {
            "inquiry_type": forms.Select(attrs={"class": "form-select"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        inquiry_type = initial.get("inquiry_type")
        if inquiry_type:
            kwargs["initial"] = {**initial, "inquiry_type": inquiry_type}
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].required = False
        self.fields["vehicle"].queryset = Vehicle.objects.filter(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)
        self.fields["message"].label = "Nachricht"
        self.fields["email"].label = "E-Mail"
        self.fields["phone"].label = "Telefon"

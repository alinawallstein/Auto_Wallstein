from __future__ import annotations

from django import forms

from .models import CustomerInquiry, Vehicle, VehicleAIText, VehicleImage, VehicleStatus
from .selectors import public_vehicles


class VehicleFilterForm(forms.Form):
    brand = forms.CharField(required=False, max_length=100, label="Marke")
    model = forms.CharField(required=False, max_length=120, label="Modell")
    price_min = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Preis von")
    price_max = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Preis bis")
    year_min = forms.IntegerField(required=False, min_value=0, max_value=9999, label="Baujahr von")
    year_max = forms.IntegerField(required=False, min_value=0, max_value=9999, label="Baujahr bis")
    mileage_max = forms.IntegerField(required=False, min_value=0, max_value=2147483647, label="Km bis")
    fuel_type = forms.CharField(required=False, max_length=60, label="Kraftstoff")
    transmission = forms.CharField(required=False, max_length=50, label="Getriebe")
    sort = forms.ChoiceField(required=False, label="Sortierung", choices=[
        ("newest", "Neueste"), ("price_asc", "Preis aufsteigend"),
        ("price_desc", "Preis absteigend"), ("mileage", "Kilometerstand"),
    ])

    def clean(self):
        data = super().clean()
        for lower, upper in (("price_min", "price_max"), ("year_min", "year_max")):
            if data.get(lower) is not None and data.get(upper) is not None and data[lower] > data[upper]:
                self.add_error(upper, "Der Höchstwert darf nicht unter dem Mindestwert liegen.")
        return data


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
        ]
        widgets = {
            "first_registration": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "hu_valid_until": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
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

    def clean(self):
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get("purchase_price")
        sale_price = cleaned_data.get("sale_price")

        if purchase_price is not None and purchase_price < 0:
            self.add_error("purchase_price", "Der Einkaufspreis darf nicht negativ sein.")
        if sale_price is not None and sale_price < 0:
            self.add_error("sale_price", "Der Verkaufspreis darf nicht negativ sein.")
        return cleaned_data

    def field_groups(self):
        groups = [
            ("Verkauf & Bestand", ["sale_price", "mileage", "status"]),
            ("Fahrzeug", ["internal_number", "brand", "model", "variant", "vehicle_type"]),
            ("Technische Daten", ["first_registration", "year", "fuel_type", "transmission", "power_kw", "power_ps", "engine_capacity", "doors", "seats"]),
            ("Zustand & Ausstattung", ["exterior_color", "interior_equipment", "previous_owners", "hu_valid_until", "equipment", "description"]),
            ("Interne Angaben", ["purchase_price", "vin"]),
        ]
        return [(title, [self[name] for name in names]) for title, names in groups]


class VehiclePublicationForm(forms.Form):
    website_enabled = forms.BooleanField(
        required=False, label="Für die Website freigeben",
        help_text="Das Fahrzeug erscheint nur mit dem Verkaufsstatus „Verfügbar“. Bei Reservierung, Verkauf oder Vorbereitung bleibt es ausgeblendet.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )



class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if not files.getlist(name):
            return []
        return files.getlist(name)


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not isinstance(data, (list, tuple)):
            return super().clean(data, initial)

        cleaned_files = []
        for file_data in data:
            if file_data in (None, ""):
                continue
            cleaned_files.append(super().clean(file_data, initial))
        if not cleaned_files:
            # Apply required-field validation to an empty multiple upload too.
            return super().clean(None, initial)
        return cleaned_files


class VehicleImageUploadForm(forms.Form):
    images = MultipleFileField(
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
            "inquiry_type": forms.Select(attrs={"class": "aw-input"}),
            "vehicle": forms.Select(attrs={"class": "aw-input"}),
            "name": forms.TextInput(attrs={"class": "aw-input"}),
            "email": forms.EmailInput(attrs={"class": "aw-input"}),
            "phone": forms.TextInput(attrs={"class": "aw-input"}),
            "message": forms.Textarea(attrs={"class": "aw-input", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        inquiry_type = initial.get("inquiry_type")
        if inquiry_type:
            kwargs["initial"] = {**initial, "inquiry_type": inquiry_type}
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].required = False
        self.fields["vehicle"].queryset = public_vehicles()
        self.fields["message"].label = "Nachricht"
        self.fields["email"].label = "E-Mail"
        self.fields["phone"].label = "Telefon"

from django import forms
from django.core.exceptions import ValidationError

from .comparison_selection import validate_comparison
from .models import Product


class SavedComparisonForm(forms.Form):
    title = forms.CharField(
        label="Comparison title",
        max_length=120,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "id": "compare-save-title",
                "class": "form-control compare-save-title",
                "placeholder": "Plant-based milk options",
                "autocomplete": "off",
                "aria-describedby": "compare-save-title-errors",
            }
        ),
    )

    def __init__(self, *args, selected_barcodes, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_barcodes = selected_barcodes

    def clean(self):
        cleaned_data = super().clean()

        try:
            barcodes = validate_comparison(self.selected_barcodes)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

        available_barcodes = set(
            Product.objects.filter(
                barcode__in=barcodes,
            ).values_list("barcode", flat=True)
        )

        if any(barcode not in available_barcodes for barcode in barcodes):
            raise forms.ValidationError(
                "One or more selected products are no longer available. "
                "Please update your selection."
            )

        cleaned_data["barcodes"] = barcodes
        return cleaned_data
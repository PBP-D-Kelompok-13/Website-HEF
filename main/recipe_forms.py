from django import forms
from django.forms import BaseFormSet, formset_factory
from django.urls import reverse

from .models import SavedRecipe


class RecipeIngredientForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "e.g. Quinoa",
    }))
    amount_g = forms.DecimalField(min_value=0.01, max_value=10000, max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 100", "step": "0.01"}))

    def __init__(self, *args, require_weight=True, **kwargs):
        self.require_weight = require_weight
        super().__init__(*args, **kwargs)
        self.fields["amount_g"].required = require_weight
        suggestions_id = f"{self['name'].id_for_label}-suggestions"
        self.fields["name"].widget.attrs.update({
            "list": suggestions_id,
            "autocomplete": "off",
            "hx-get": reverse("main:recipe_ingredient_suggestions"),
            "hx-trigger": "input changed delay:300ms",
            "hx-include": "this",
            "hx-target": f"#{suggestions_id}",
            "hx-swap": "innerHTML",
        })

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class RecipeIngredientFormSetBase(BaseFormSet):
    deletion_widget = forms.HiddenInput


RecipeIngredientFormSet = formset_factory(
    RecipeIngredientForm, extra=3, can_delete=True, min_num=1, validate_min=True,
    max_num=30, validate_max=True, formset=RecipeIngredientFormSetBase,
)


class RecipeAuthorForm(forms.ModelForm):
    class Meta:
        model = SavedRecipe
        fields = ("title", "description", "instructions", "servings", "photo")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 120,
                                           "placeholder": "e.g. Roasted Vegetable Quinoa Bowl"}),
            "description": forms.Textarea(attrs={"class": "form-control hef-recipe-textarea", "rows": 3,
                                                  "style": "resize: none; max-height: 320px; overflow-y: hidden;",
                                                  "placeholder": "A short description of your recipe"}),
            "instructions": forms.Textarea(attrs={"class": "form-control hef-recipe-textarea", "rows": 5,
                                                   "style": "resize: none; max-height: 320px; overflow-y: hidden;",
                                                   "placeholder": "Add one instruction step per line"}),
            "servings": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 50}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["instructions"].required = False
        self.fields["photo"].required = False

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_servings(self):
        servings = self.cleaned_data["servings"]
        if not 1 <= servings <= 50:
            raise forms.ValidationError("Servings must be between 1 and 50.")
        return servings

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo or not getattr(photo, "size", None):
            return photo
        if photo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("The photo must be 10 MB or smaller.")
        if photo.content_type not in {"image/jpeg", "image/png"}:
            raise forms.ValidationError("Upload a JPG or PNG image.")
        signature = photo.read(8)
        photo.seek(0)
        if not (signature.startswith(b"\xff\xd8\xff") or signature.startswith(b"\x89PNG\r\n\x1a\n")):
            raise forms.ValidationError("The uploaded file is not a valid JPG or PNG image.")
        return photo

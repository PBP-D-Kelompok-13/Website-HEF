from .comparison_selection import validate_comparison
from datetime import date
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When
from django.urls import reverse



class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()

    REQUIRED_FIELDS = ["email", "date_of_birth"]

    def __str__(self):
        return self.username


class SavedRecipe(models.Model):
    class Source(models.TextChoices):
        OWN = "own", "My recipe"
        SPOONACULAR = "spoonacular", "Spoonacular"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_recipes")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.OWN)
    spoonacular_id = models.PositiveBigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=4000)
    ingredients = models.TextField(max_length=4000)
    ingredient_items = models.JSONField(default=list, blank=True)
    instructions = models.TextField(blank=True, max_length=10000)
    servings = models.PositiveSmallIntegerField(default=1)
    ready_in_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    health_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    diets = models.JSONField(default=list, blank=True)
    nutrition = models.JSONField(default=dict, blank=True)
    image_url = models.URLField(blank=True)
    photo = models.FileField(upload_to="recipe_photos/", blank=True)
    source_url = models.URLField(blank=True)
    is_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "spoonacular_id"],
                condition=models.Q(source="spoonacular", spoonacular_id__isnull=False),
                name="unique_user_spoonacular_recipe",
            ),
        ]

    def __str__(self):
        return self.title
class Ingredient(models.Model):
    CATEGORY_CHOICES = [
        ('Vegetables', 'Vegetables'),
        ('Fruits', 'Fruits'),
        ('Dairy & Eggs', 'Dairy & Eggs'),
        ('Protein', 'Protein'),
        ('Carbohydrates', 'Carbohydrates'),
        ('Drinks', 'Drinks'),
        ('Condiments', 'Condiments'),
        ('Snacks', 'Snacks'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    quantity = models.CharField(max_length=50)
    expiration_date = models.DateField()
    image = models.ImageField(upload_to='ingredients/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def days_until_expiry(self):
        if not self.expiration_date:
            return None
        return (self.expiration_date - date.today()).days


class ProductQuerySet(models.QuerySet):
    def search(self, query):
        query = (query or "").strip()
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(barcode__icontains=query)
        )

    def filter_by(self, category="", eco="", nutri="", saved_by=None, sort="eco"):
        qs = self
        if category and category != "all":
            qs = qs.filter(category__iexact=category)
        if eco in {"a", "b", "c", "d", "e"}:
            qs = qs.filter(eco_grade__iexact=eco)
        if nutri in {"a", "b", "c", "d", "e"}:
            qs = qs.filter(nutri_grade__iexact=nutri)
        if saved_by and saved_by.is_authenticated:
            qs = qs.filter(bookmarks__user=saved_by)
        if sort == "name":
            return qs.order_by("name")
        if sort == "newest":
            return qs.order_by("-created_at")
        return qs.annotate(
            _empty_eco=Case(
                When(eco_grade="", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("_empty_eco", "eco_grade", "name")

    def with_saved_flag(self, user):
        if user and user.is_authenticated:
            subquery = Bookmark.objects.filter(user=user, product=OuterRef("pk"))
            return self.annotate(is_saved=Exists(subquery))
        return self.annotate(is_saved=Value(False, output_field=models.BooleanField()))


class Product(models.Model):
    GRADES = [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("e", "E")]
    CATEGORIES = [
        ("Beverages", "Beverages"),
        ("Snacks", "Snacks"),
        ("Breakfast", "Breakfast"),
        ("Pantry staples", "Pantry staples"),
        ("Other", "Other"),
    ]
    LEVELS = [("low", "Low"), ("moderate", "Moderate"), ("high", "High")]
    NOVA = [
        (1, "Group 1 - Unprocessed or minimally processed"),
        (2, "Group 2 - Processed culinary ingredients"),
        (3, "Group 3 - Processed foods"),
        (4, "Group 4 - Ultra-processed foods"),
    ]
    ECO_SUMMARIES = {
        "a": "Very low environmental impact",
        "b": "Low environmental impact",
        "c": "Moderate environmental impact",
        "d": "High environmental impact",
        "e": "Very high environmental impact",
    }
    NUTRI_SUMMARIES = {
        "a": "Strong nutritional quality",
        "b": "Good nutritional quality",
        "c": "Balanced — enjoy mindfully",
        "d": "Lower nutritional quality",
        "e": "Limit — high in calories, sugar, or fat",
    }

    barcode = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=64, choices=CATEGORIES, default="Other")
    quantity = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    labels = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated labels, e.g. Organic, Vegan"
    )

    eco_grade = models.CharField(max_length=1, choices=GRADES, blank=True, default="")
    nutri_grade = models.CharField(max_length=1, choices=GRADES, blank=True, default="")
    nova_group = models.PositiveSmallIntegerField(choices=NOVA, null=True, blank=True)

    sugars_100g = models.FloatField(null=True, blank=True)
    sugars_level = models.CharField(max_length=16, choices=LEVELS, blank=True)
    salt_100g = models.FloatField(null=True, blank=True)
    salt_level = models.CharField(max_length=16, choices=LEVELS, blank=True)
    fat_100g = models.FloatField(null=True, blank=True)
    fat_level = models.CharField(max_length=16, choices=LEVELS, blank=True)
    calories_100g = models.FloatField(null=True, blank=True)
    kj_100g = models.FloatField(null=True, blank=True)
    fiber_100g = models.FloatField(null=True, blank=True)

    co2_kg = models.FloatField(null=True, blank=True)
    co2_agriculture = models.FloatField(null=True, blank=True)
    co2_processing = models.FloatField(null=True, blank=True)
    co2_packaging = models.FloatField(null=True, blank=True)
    co2_transport = models.FloatField(null=True, blank=True)
    origin = models.CharField(max_length=255, blank=True)
    packaging = models.CharField(max_length=255, blank=True)
    ingredients = models.TextField(blank=True)
    allergens = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.barcode})"

    def get_absolute_url(self):
        return reverse("main:product_detail", args=[self.barcode])

    @property
    def eco_summary(self):
        return self.ECO_SUMMARIES.get(self.eco_grade, "Eco-Score not available")

    @property
    def nutri_summary(self):
        return self.NUTRI_SUMMARIES.get(self.nutri_grade, "Nutri-Score not available")

    @property
    def label_list(self):
        return [item.strip() for item in self.labels.split(",") if item.strip()][:3]

    @property
    def co2_parts(self):
        raw = [
            ("Growing", self.co2_agriculture or 0, "forest"),
            ("Production", self.co2_processing or 0, "citrus"),
            (
                "Packaging & transport",
                (self.co2_packaging or 0) + (self.co2_transport or 0),
                "watermelon",
            ),
        ]
        total = sum(val for _, val, _ in raw)
        if total <= 0:
            return []
        return [
            {
                "label": label,
                "value": round(val, 2),
                "pct": round(val / total * 100, 1),
                "tone": tone,
            }
            for label, val, tone in raw
            if val > 0
        ]

    def to_dict(self):
        return {
            "barcode": self.barcode,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "quantity": self.quantity,
            "image_url": self.image_url,
            "eco_grade": self.eco_grade or None,
            "nutri_grade": self.nutri_grade or None,
            "nova_group": self.nova_group,
            "co2_kg": self.co2_kg,
            "nutrition_per_100g": {
                "sugars": self.sugars_100g,
                "salt": self.salt_100g,
                "fat": self.fat_100g,
                "calories": self.calories_100g,
                "fiber": self.fiber_100g,
            },
        }


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="bookmarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_user_product_bookmark"
            )
        ]
        
class SavedComparison(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_comparisons",
    )
    title = models.CharField(max_length=120)
    barcodes = models.JSONField(
        default=list,
        validators=[validate_comparison],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.title

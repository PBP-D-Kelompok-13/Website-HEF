from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser


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

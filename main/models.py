from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date

class CustomUser(AbstractUser):
    email = models.EmailField(unique = True)
    date_of_birth = models.DateField()

    # Required fields when creating a superuser
    REQUIRED_FIELDS = ['email', 'date_of_birth']

    def __str__(self):
        return self.username
    
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
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def days_until_expiry(self):
        if not self.expiration_date:
            return None
        return (self.expiration_date - date.today()).days

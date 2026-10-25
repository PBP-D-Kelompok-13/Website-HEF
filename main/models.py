from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique = True)
    date_of_birth = models.DateField()

    # Required fields when creating a superuser
    REQUIRED_FIELDS = ['email', 'date_of_birth']

    def __str__(self):
        return self.username 

from datetime import date
from django.contrib.auth import get_user_model
from main.models import Product

User = get_user_model()
_counter = 0


def make_user(username="healthyuser", **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        date_of_birth=date(2000, 1, 1),
        **extra,
    )


def make_product(**overrides):
    global _counter
    _counter += 1
    data = {
        "barcode": f"20000000{_counter:05d}",
        "name": f"Product {_counter}",
        "brand": "Test Brand",
        "category": "Beverages",
        "eco_grade": "a",
        "nutri_grade": "b",
    }
    data.update(overrides)
    return Product.objects.create(**data)

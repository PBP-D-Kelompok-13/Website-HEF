from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from main.forms import *
from main.models import *

class PantryFeatureAcceptanceTest(TestCase):
    def test_user_pantry_management_journey(self):
        user = CustomUser.objects.create_user(
            username="celine",
            email="celine@example.com",
            date_of_birth=date(2005, 1, 1),
            password="Password123!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("main:show_inventory"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/inventory.html")

        response = self.client.post(reverse("main:add_ingredient"), {
            "name": "Broccoli",
            "category": "Vegetables",
            "quantity": "2 pcs",
            "expiration_date": "2026-11-05"
        })
        self.assertRedirects(response, reverse("main:show_inventory"))
        self.assertEqual(Ingredient.objects.count(), 1)
        
        response = self.client.get(reverse("main:show_inventory"))
        self.assertContains(response, "Broccoli")
        
class IngredientModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="celine",
            email="celine@example.com",
            date_of_birth=date(2005, 1, 1),
            password="Password123!"
        )

    def test_ingredient_creation_and_string_representation(self):
        ingredient = Ingredient.objects.create(
            user=self.user,
            name="Milk",
            category="Dairy & Eggs",
            quantity="1 bottle",
            expiration_date=date(2026, 11, 2)
        )
        self.assertEqual(ingredient.name, "Milk")
        self.assertEqual(ingredient.category, "Dairy & Eggs")
        self.assertEqual(str(ingredient), "Milk (celine)")
        
class IngredientFormTests(TestCase):
    def test_ingredient_form_accepts_valid_category_choices(self):
        form_data = {
            "name": "Apples",
            "category": "Fruits",
            "quantity": "1 kg",
            "expiration_date": "2026-11-10"
        }
        form = IngredientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_ingredient_form_rejects_invalid_category(self):
        form_data = {
            "name": "Unknown Item",
            "category": "InvalidCategory",
            "quantity": "1",
            "expiration_date": "2026-11-10"
        }
        form = IngredientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

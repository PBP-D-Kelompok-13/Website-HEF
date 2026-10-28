from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from main.models import SavedRecipe

User = get_user_model()


class RecipeAnalyzerFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="flowcook", email="flow@example.com", password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.client.force_login(self.user)

    @patch("main.views.search_spoonacular_recipes")
    def test_discover_page_searches_with_diet_and_time_filters(self, search):
        search.return_value = {"results": [{"id": 123, "title": "Tofu Bowl"}], "totalResults": 1, "offset": 0}
        response = self.client.get(reverse("main:recipe_discover"), {
            "query": "tofu", "diet": "vegan", "maxReadyTime": "30",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/recipes/discover.html")
        self.assertContains(response, "Discover")
        self.assertContains(response, "Tofu Bowl")
        search.assert_called_once_with(query="tofu", diet="vegan", max_ready_time=30, offset=0)

    @patch("main.views.analyze_with_spoonacular")
    def test_create_accepts_weighted_ingredient_rows_and_saves_description(self, analyze):
        analyze.return_value = {"healthScore": 76, "nutrition": {"nutrients": []}}
        response = self.client.post(reverse("main:recipe_create"), {
            "title": "Roasted veggie bowl", "servings": 4,
            "description": "Quinoa with roasted vegetables.",
            "ingredient-TOTAL_FORMS": "2", "ingredient-INITIAL_FORMS": "0",
            "ingredient-MIN_NUM_FORMS": "0", "ingredient-MAX_NUM_FORMS": "30",
            "ingredient-0-name": "Quinoa", "ingredient-0-amount_g": "180",
            "ingredient-1-name": "Spinach", "ingredient-1-amount_g": "100",
            "instructions": "Roast vegetables.\nServe warm.", "action": "analyze",
        })
        recipe = SavedRecipe.objects.get(title="Roasted veggie bowl")
        self.assertEqual(recipe.description, "Quinoa with roasted vegetables.")
        self.assertEqual(recipe.ingredient_items[0], {"name": "Quinoa", "amount_g": "180"})
        self.assertEqual(recipe.health_score, 76)
        analyze.assert_called_once()
        self.assertRedirects(response, reverse("main:recipe_detail", args=[recipe.pk]))

    @patch("main.views.analyze_with_spoonacular")
    def test_save_as_draft_does_not_call_spoonacular(self, analyze):
        response = self.client.post(reverse("main:recipe_create"), {
            "title": "My draft", "servings": 2, "description": "A draft.",
            "ingredient-TOTAL_FORMS": "1", "ingredient-INITIAL_FORMS": "0",
            "ingredient-MIN_NUM_FORMS": "0", "ingredient-MAX_NUM_FORMS": "30",
            "ingredient-0-name": "Beans", "ingredient-0-amount_g": "200",
            "action": "draft",
        })
        draft = SavedRecipe.objects.get(title="My draft")
        self.assertTrue(draft.is_draft)
        analyze.assert_not_called()
        self.assertRedirects(response, reverse("main:recipe_detail", args=[draft.pk]))


    def test_anonymous_user_cannot_access_discover(self):
        self.client.logout()
        url = reverse("main:recipe_discover")
        self.assertRedirects(self.client.get(url), f"{reverse('main:login_account')}?next={url}")

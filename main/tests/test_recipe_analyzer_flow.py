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
        self.assertContains(response, 'class="hef-bookmark-icon"')
        self.assertNotContains(response, "▮")
        self.assertContains(response, 'data-bs-target="#saveRecipeModal-123"')
        self.assertContains(response, 'id="saveRecipeModal-123"')
        self.assertContains(response, "Are you sure you want to save this recipe?")
        self.assertContains(response, "Yes, save recipe")
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

    @patch("main.views.get_spoonacular_recipe")
    def test_save_spoonacular_recipe_creates_user_scoped_saved_entry(self, get_recipe):
        get_recipe.return_value = {
            "id": 123, "title": "Tofu Bowl", "image": "https://img.example/tofu.jpg",
            "readyInMinutes": 25, "servings": 2, "healthScore": 80,
            "diets": ["vegan"], "nutrition": {"nutrients": []},
            "extendedIngredients": [{"name": "tofu", "amount": 200, "unit": "g", "original": "200 g tofu"}],
            "analyzedInstructions": [], "summary": "A tofu bowl.", "sourceUrl": "https://example.com/tofu",
        }
        response = self.client.post(reverse("main:recipe_save_spoonacular", args=[123]))
        saved = SavedRecipe.objects.get(user=self.user, spoonacular_id=123)
        self.assertEqual(saved.source, SavedRecipe.Source.SPOONACULAR)
        self.assertEqual(saved.title, "Tofu Bowl")
        self.assertEqual(saved.ingredient_items[0]["name"], "tofu")
        self.assertRedirects(response, reverse("main:recipe_saved_list"))

    def test_saved_page_separates_spoonacular_from_my_recipes(self):
        SavedRecipe.objects.create(user=self.user, title="My Soup", ingredients="beans", servings=1)
        SavedRecipe.objects.create(
            user=self.user, title="Saved Tofu", ingredients="tofu", servings=2,
            source=SavedRecipe.Source.SPOONACULAR, spoonacular_id=123,
        )
        response = self.client.get(reverse("main:recipe_saved_list"))
        self.assertContains(response, "From Spoonacular")
        self.assertContains(response, "My recipes")
        self.assertContains(response, "Saved Tofu")
        self.assertContains(response, "My Soup")
        self.assertContains(response, 'class="hef-trash-icon"')
        self.assertContains(response, 'data-bs-target="#removeSavedRecipeModal-')
        self.assertContains(response, "Are you sure you want to remove this recipe?")
        self.assertNotContains(response, "▮")

    def test_anonymous_user_cannot_access_discover(self):
        self.client.logout()
        url = reverse("main:recipe_discover")
        self.assertRedirects(self.client.get(url), f"{reverse('main:login_account')}?next={url}")

    @patch("main.views.search_spoonacular_ingredients")
    def test_ingredient_suggestions_return_known_ingredients(self, search):
        search.return_value = [{"name": "quinoa"}, {"name": "quinoa flakes"}]
        response = self.client.get(reverse("main:recipe_ingredient_suggestions"), {"q": "quin"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="quinoa">', html=True)
        self.assertContains(response, '<option value="quinoa flakes">', html=True)
        search.assert_called_once_with("quin")

    @patch("main.views.search_spoonacular_ingredients")
    def test_ingredient_suggestions_ignore_short_queries(self, search):
        response = self.client.get(reverse("main:recipe_ingredient_suggestions"), {"q": "q"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<option")
        search.assert_not_called()

    def test_create_form_aligns_recipe_details_with_help_and_ingredients_with_instructions(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="row g-3 align-items-stretch"')
        self.assertContains(response, 'class="hef-recipe-panel p-3 p-md-4 h-100"')
        self.assertContains(response, 'class="hef-recipe-help h-100"')
        self.assertContains(response, 'type="hidden" name="ingredient-0-DELETE"')

    def test_create_form_limits_initial_ingredient_rows_and_aligns_clear_action(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertEqual(response.context["ingredient_formset"].total_form_count(), 4)
        self.assertContains(response, 'id="recipe-actions" class="col-12 col-xl-7 d-flex justify-content-end"')
        self.assertLess(response.content.index(b"Save as draft"), response.content.index(b"Clear form"))

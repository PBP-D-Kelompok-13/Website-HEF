from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from main.forms import RecipeForm
from main.models import SavedRecipe

User = get_user_model()


class RecipeAnalyzerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="cook", email="cook@example.com", password="StrongPass123!", date_of_birth=date(2000, 1, 1))
        self.other = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123!", date_of_birth=date(2000, 1, 1))
        self.client.force_login(self.owner)
        self.recipe = SavedRecipe.objects.create(user=self.owner, title="Lentil bowl", ingredients="1 cup lentils\n1 tomato", instructions="Cook the lentils.", servings=2, nutrition={"nutrition": {"nutrients": []}})

    def test_form_validates_required_ingredients_and_serving_range(self):
        valid = RecipeForm({"title": "Green soup", "ingredients": "2 cups spinach\n1 onion", "instructions": "Blend.", "servings": 2})
        self.assertTrue(valid.is_valid(), valid.errors)
        invalid = RecipeForm({"title": "Soup", "ingredients": " ", "servings": 0})
        self.assertFalse(invalid.is_valid())
        self.assertIn("ingredients", invalid.errors)
        self.assertIn("servings", invalid.errors)

    def test_anonymous_cannot_read_recipes(self):
        self.client.logout()
        url = reverse("main:recipe_list")
        self.assertRedirects(self.client.get(url), f"{reverse('main:login_account')}?next={url}")

    def test_list_and_detail_only_expose_owned_recipes(self):
        SavedRecipe.objects.create(user=self.other, title="Private curry", ingredients="rice", servings=1)
        response = self.client.get(reverse("main:recipe_list"))
        self.assertContains(response, "Lentil bowl")
        self.assertNotContains(response, "Private curry")
        detail = reverse("main:recipe_detail", args=[self.recipe.pk])
        detail_response = self.client.get(detail)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, f'data-bs-target="#removeRecipeModal-{self.recipe.pk}"')
        self.assertContains(detail_response, f'id="removeRecipeModal-{self.recipe.pk}"')
        self.assertContains(detail_response, "max-width: 400px")
        self.assertContains(detail_response, "grid-template-columns: repeat(2")
        self.assertContains(detail_response, "recipe_analyzer.css?v=recipe-modal-layout-3")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(detail).status_code, 404)

    @patch("main.views.analyze_with_spoonacular")
    def test_create_calls_spoonacular_and_saves_for_owner(self, analyze):
        analyze.return_value = {"nutrition": {"nutrients": [{"name": "Calories", "amount": 210, "unit": "kcal"}]}}
        response = self.client.post(reverse("main:recipe_create"), {"title": "Bean salad", "ingredients": "1 cup beans\n1 tomato", "instructions": "Mix.", "servings": 2})
        saved = SavedRecipe.objects.get(title="Bean salad")
        self.assertEqual(saved.user, self.owner)
        self.assertEqual(saved.nutrition["nutrition"]["nutrients"][0]["amount"], 210)
        self.assertRedirects(response, reverse("main:recipe_detail", args=[saved.pk]))
        analyze.assert_called_once()

    def test_detail_escapes_untrusted_recipe_title(self):
        self.recipe.title = "<script>alert(1)</script>"
        self.recipe.save(update_fields=["title"])
        response = self.client.get(reverse("main:recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_htmx_delete_returns_redirect_header(self):
        response = self.client.post(
            reverse("main:recipe_delete", args=[self.recipe.pk]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], reverse("main:recipe_list"))
        self.assertFalse(SavedRecipe.objects.filter(pk=self.recipe.pk).exists())

    def test_update_delete_and_method_restriction(self):
        update = reverse("main:recipe_update", args=[self.recipe.pk])
        delete = reverse("main:recipe_delete", args=[self.recipe.pk])
        self.assertEqual(self.client.get(delete).status_code, 405)
        with patch("main.views.analyze_with_spoonacular", return_value={"nutrition": {}}):
            response = self.client.post(update, {"title": "Updated lentils", "ingredients": "1 cup lentils", "instructions": "Simmer.", "servings": 3})
        self.assertRedirects(response, reverse("main:recipe_detail", args=[self.recipe.pk]))
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "Updated lentils")
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(delete).status_code, 404)
        self.assertTrue(SavedRecipe.objects.filter(pk=self.recipe.pk).exists())
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(delete), reverse("main:recipe_list"))
        self.assertFalse(SavedRecipe.objects.filter(pk=self.recipe.pk).exists())

    @patch("main.views.analyze_with_spoonacular")
    def test_invalid_create_does_not_call_api_or_save(self, analyze):
        response = self.client.post(reverse("main:recipe_create"), {"title": "Soup", "ingredients": "", "servings": 2})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(analyze.called)
        self.assertFalse(SavedRecipe.objects.filter(title="Soup").exists())

    def test_create_rejects_missing_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(reverse("main:recipe_create"), {"title": "Soup", "ingredients": "1 carrot", "servings": 1})
        self.assertEqual(response.status_code, 403)


class SpoonacularServiceTests(TestCase):
    @patch("main.services.recipe_analyzer.requests.post")
    def test_service_sends_key_and_recipe_payload_to_analysis_endpoint(self, post):
        from unittest.mock import patch as patch_context
        from main.services.recipe_analyzer import SPOONACULAR_ANALYZE_URL, analyze_with_spoonacular

        post.return_value.json.return_value = {"nutrition": {}}
        with patch_context.dict("os.environ", {"SPOONACULAR_API_KEY": "test-key"}):
            result = analyze_with_spoonacular(title="Bean bowl", ingredients="1 cup beans\n1 tomato", instructions="Mix", servings=2)
        self.assertEqual(result, {"nutrition": {}})
        post.assert_called_once_with(
            SPOONACULAR_ANALYZE_URL,
            params={"apiKey": "test-key", "includeNutrition": "true"},
            json={"title": "Bean bowl", "servings": 2, "ingredients": ["1 cup beans", "1 tomato"], "instructions": "Mix"},
            timeout=12,
        )

from datetime import date
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from main.models import SavedRecipe
from main.views import _display_analysis, _instruction_steps

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

    @patch("main.views.search_spoonacular_recipes")
    def test_discover_sanitizes_filters_and_handles_api_failure(self, search):
        search.side_effect = ValueError("invalid API payload")

        response = self.client.get(
            reverse("main:recipe_discover"),
            {"diet": "unknown", "maxReadyTime": "2000", "offset": "bad"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/recipes/_discover_results.html")
        self.assertContains(response, "temporarily unavailable")
        search.assert_called_once_with(query="", diet="", max_ready_time=None, offset=0)

    @patch("main.views.search_spoonacular_recipes")
    def test_discover_invalid_time_and_load_more_use_htmx_partial(self, search):
        search.return_value = {"results": [], "totalResults": 20, "offset": 6}

        response = self.client.get(
            reverse("main:recipe_discover"),
            {"diet": "vegan", "maxReadyTime": "fast", "offset": "6"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/recipes/_discover_more.html")
        search.assert_called_once_with(query="", diet="vegan", max_ready_time=None, offset=6)

    def test_recipe_display_helpers_handle_empty_values_and_instruction_shapes(self):
        self.assertEqual(_display_analysis(None)["calories"], 0)
        self.assertEqual(
            _instruction_steps([{"steps": [{"step": "Mix"}, {"step": ""}]}]),
            ["Mix"],
        )
        self.assertEqual(_instruction_steps(" Chop\n\nServe "), ["Chop", "Serve"])

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

    def test_saved_page_filters_by_title_and_falls_back_to_default_sort(self):
        SavedRecipe.objects.create(user=self.user, title="Tofu bowl", ingredients="tofu")
        SavedRecipe.objects.create(user=self.user, title="Bean soup", ingredients="beans")

        response = self.client.get(
            reverse("main:recipe_saved_list"), {"query": "tofu", "sort": "unknown"}
        )

        self.assertContains(response, "Tofu bowl")
        self.assertNotContains(response, "Bean soup")
        self.assertEqual(response.context["sort"], "newest")

    def test_saved_spoonacular_detail_reads_nested_nutrition_and_instructions(self):
        recipe = SavedRecipe.objects.create(
            user=self.user,
            source=SavedRecipe.Source.SPOONACULAR,
            spoonacular_id=456,
            title="Saved tofu",
            ingredients="200 g tofu",
            ingredient_items=[{"name": "tofu", "amount": 200, "unit": "g"}],
            nutrition={
                "nutrition": {"nutrients": []},
                "analyzedInstructions": [{"steps": [{"step": "Bake the tofu."}]}],
            },
            instructions="",
            servings=2,
        )

        response = self.client.get(reverse("main:recipe_detail", args=[recipe.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bake the tofu.")
        self.assertContains(response, "200 g")

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

    def test_create_form_explains_analysis_inputs_and_results_clearly(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertContains(response, "• Enter each ingredient with its amount in grams.")
        self.assertContains(response, "• Nutrition values are estimates per serving based on the ingredients provided.")
        self.assertContains(response, "• Health score and dietary labels are shown only when Spoonacular returns them.")
        self.assertContains(response, "• Save as draft to keep working on your recipe later.")
        self.assertContains(response, "• Add clear preparation steps so you can follow the recipe later.")

    def test_create_form_limits_initial_ingredient_rows_and_aligns_clear_action(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertEqual(response.context["ingredient_formset"].total_form_count(), 4)
        self.assertContains(response, 'id="recipe-actions" class="col-12 col-xl-7 d-flex justify-content-end"')
        self.assertLess(response.content.index(b"Save as draft"), response.content.index(b"Clear form"))

    def test_description_and_instructions_use_non_resizable_auto_growing_fields(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertContains(response, 'class="form-control hef-recipe-textarea"', count=2)
        self.assertContains(response, 'querySelectorAll(\'.hef-recipe-textarea[name="instructions"]\')')
        self.assertContains(response, "resize: none; max-height: 320px")
        self.assertContains(response, "recipe_analyzer.css?v=recipe-description-align-1")

    def test_create_form_uses_rounded_input_styles(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertContains(response, 'class="mt-3 hef-recipe-create-form"')
        self.assertContains(response, "recipe_analyzer.css?v=recipe-description-align-1")

    def test_description_field_stretches_to_match_photo_upload(self):
        response = self.client.get(reverse("main:recipe_create"))

        self.assertRegex(
            response.content.decode(),
            r'<div class="col-md-6 hef-recipe-description-field">\s*<label class="form-label" for="id_description">Description</label>',
        )
        self.assertContains(response, "recipe_analyzer.css?v=recipe-description-align-1")

    @patch("main.views.analyze_with_spoonacular", side_effect=ValueError("API error"))
    def test_create_renders_form_when_spoonacular_analysis_fails(self, analyze):
        response = self.client.post(reverse("main:recipe_create"), {
            "title": "Carrot soup", "ingredients": "1 carrot", "servings": 2,
        })

        self.assertEqual(response.status_code, 502)
        self.assertTemplateUsed(response, "pages/recipes/form.html")
        self.assertTrue(response.context["form"].is_bound)
        analyze.assert_called_once()

    def test_update_get_restores_legacy_ingredients_and_post_can_save_draft(self):
        recipe = SavedRecipe.objects.create(
            user=self.user, title="Old beans", ingredients="Black beans\nOnion", servings=2,
        )
        edit_url = reverse("main:recipe_update", args=[recipe.pk])

        get_response = self.client.get(edit_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.context["ingredient_formset"].initial,
            [{"name": "Black beans", "amount_g": ""}, {"name": "Onion", "amount_g": ""}],
        )

        post_response = self.client.post(edit_url, {
            "title": "Updated beans", "servings": 3, "action": "draft",
        })

        recipe.refresh_from_db()
        self.assertRedirects(post_response, reverse("main:recipe_detail", args=[recipe.pk]))
        self.assertTrue(recipe.is_draft)
        self.assertEqual(recipe.ingredient_items[0], {"name": "Black beans", "amount_g": ""})

    @patch("main.views.analyze_with_spoonacular", side_effect=requests.RequestException("API unavailable"))
    def test_update_renders_form_when_reanalysis_fails(self, analyze):
        recipe = SavedRecipe.objects.create(
            user=self.user, title="Old beans", ingredients="Black beans", servings=2,
        )
        response = self.client.post(reverse("main:recipe_update", args=[recipe.pk]), {
            "title": "Updated beans", "servings": 3,
            "ingredient-TOTAL_FORMS": "1", "ingredient-INITIAL_FORMS": "0",
            "ingredient-MIN_NUM_FORMS": "1", "ingredient-MAX_NUM_FORMS": "30",
            "ingredient-0-name": "Black beans", "ingredient-0-amount_g": "150",
        })

        self.assertEqual(response.status_code, 502)
        self.assertTemplateUsed(response, "pages/recipes/form.html")
        analyze.assert_called_once()

    @patch("main.views.get_spoonacular_recipe")
    def test_spoonacular_detail_and_duplicate_htmx_save(self, get_recipe):
        payload = {
            "id": 123, "title": "Tofu bowl", "summary": "<b>A tofu bowl.</b>",
            "sourceUrl": "https://example.com/tofu", "readyInMinutes": 20,
            "healthScore": 75, "image": "https://img.example/tofu.jpg", "servings": 2,
            "nutrition": {"nutrition": {"nutrients": []}},
            "extendedIngredients": [{"original": "200 g tofu"}],
            "analyzedInstructions": [{"steps": [{"step": "Bake the tofu."}]}],
        }
        get_recipe.return_value = payload

        detail_response = self.client.get(
            reverse("main:recipe_spoonacular_detail", args=[123]), {"query": "tofu"}
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Bake the tofu.")
        self.assertContains(detail_response, "A tofu bowl.")
        self.assertContains(
            detail_response,
            '<progress class="hef-score-progress mb-3" value="75" max="100" aria-label="Health score"></progress>',
            html=True,
        )

        SavedRecipe.objects.create(
            user=self.user, source=SavedRecipe.Source.SPOONACULAR, spoonacular_id=123,
            title="Tofu bowl", ingredients="200 g tofu", servings=2,
        )
        save_response = self.client.post(
            reverse("main:recipe_save_spoonacular", args=[123]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(save_response["HX-Redirect"], reverse("main:recipe_saved_list"))
        self.assertEqual(SavedRecipe.objects.filter(user=self.user, spoonacular_id=123).count(), 1)
        self.assertEqual(get_recipe.call_count, 2)

    @patch("main.views.get_spoonacular_recipe", side_effect=ValueError("API error"))
    def test_spoonacular_detail_and_save_failures_return_to_discover(self, get_recipe):
        detail_response = self.client.get(
            reverse("main:recipe_spoonacular_detail", args=[321])
        )
        save_response = self.client.post(
            reverse("main:recipe_save_spoonacular", args=[321])
        )

        self.assertRedirects(detail_response, reverse("main:recipe_discover"))
        self.assertRedirects(save_response, reverse("main:recipe_discover"))
        self.assertEqual(get_recipe.call_count, 2)

    @patch("main.views.search_spoonacular_ingredients", side_effect=ValueError("API error"))
    def test_ingredient_suggestions_fail_gracefully(self, search):
        response = self.client.get(reverse("main:recipe_ingredient_suggestions"), {"q": "beans"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<option")
        search.assert_called_once_with("beans")

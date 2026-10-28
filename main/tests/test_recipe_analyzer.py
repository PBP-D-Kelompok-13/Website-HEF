from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from main.models import SavedRecipe

User = get_user_model()

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

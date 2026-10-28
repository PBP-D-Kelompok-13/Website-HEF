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

    def test_anonymous_user_cannot_access_discover(self):
        self.client.logout()
        url = reverse("main:recipe_discover")
        self.assertRedirects(self.client.get(url), f"{reverse('main:login_account')}?next={url}")

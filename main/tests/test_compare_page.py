from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ComparePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="compare_tester",
            email="compare@example.com",
            password="TestPassword123!",
            date_of_birth=date(2000, 1, 1),
        )

    def test_guest_is_redirected_to_login(self):
        url = reverse("main:show_compare")

        response = self.client.get(url)

        login_url = reverse("main:login_account")
        self.assertRedirects(
            response,
            f"{login_url}?next={url}",
            fetch_redirect_response=False,
        )

    def test_logged_in_user_can_open_empty_comparison(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("main:show_compare"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/compare.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Compare Products")
        self.assertContains(
            response,
            "Select 2–3 different products to compare.",
        )

    def test_navigation_links_to_compare_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("main:show_landing_page")
        )

        compare_url = reverse("main:show_compare")
        self.assertContains(
            response,
            f'href="{compare_url}"',
            count=2,
        )
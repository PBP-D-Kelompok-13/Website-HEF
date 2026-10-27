from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
HTMX = {"HTTP_HX_REQUEST": "true"}

class NavbarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.url = reverse("main:show_landing_page")

    def test_anonymous_landing_page_shows_auth_links_and_hides_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/landing_page.html")
        self.assertContains(response, "login-link", count=2)
        self.assertNotContains(response, "hef-profile-link")
        self.assertNotContains(response, "hef-navbar-username")
        self.assertContains(response, reverse("main:register_account"))

    def test_authenticated_landing_page_shows_profile_instead_of_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "hef-profile-link", count=2)
        self.assertContains(response, "hef-navbar-username", count=2)
        self.assertContains(response, "healthyuser")
        self.assertNotContains(response, "login-link")
        self.assertContains(
            response,
            f'href="{reverse("main:show_profile_page")}"',
            count=2,
        )


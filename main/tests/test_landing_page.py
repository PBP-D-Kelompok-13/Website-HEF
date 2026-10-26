from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from main.forms import CustomAuthenticationForm, CustomUserCreationForm

User = get_user_model()
HTMX = {"HTTP_HX_REQUEST": "true"}

class SitePageTests(TestCase):
    def test_landing_page_renders_shared_layout_and_content(self):
        response = self.client.get(reverse("main:show_landing_page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/landing_page.html")
        self.assertContains(response, "<nav")
        self.assertContains(response, "<footer")
        self.assertContains(response, "Healthy Eco Foody")
        self.assertContains(response, reverse("main:login_account"))
        self.assertContains(response, reverse("main:register_account"))

class NavbarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.url = reverse("main:show_landing_page")

    # --- Anonymous visitors: desktop + mobile ---
    def test_anonymous_navbar_shows_login_link_twice(self):
        response = self.client.get(self.url)
        self.assertContains(response, "login-link", count=2)

    def test_anonymous_navbar_hides_profile_link(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "hef-profile-link")
        self.assertNotContains(response, "hef-navbar-username")

    # --- Logged-in users: desktop + mobile ---
    def test_authenticated_navbar_shows_profile_link_twice(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "hef-profile-link", count=2)

    def test_authenticated_navbar_shows_username_twice(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "hef-navbar-username", count=2)
        self.assertContains(response, "healthyuser")

    def test_authenticated_navbar_hides_login_link(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "login-link")


from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date 

# Uses the correct user model from AUTH_USER_MODEL
User = get_user_model()

class BaseTemplateTests(TestCase):
    # Testing untuk base.html yang dilakukan melalui loading homepage
    def setUp(self):
        self.response = self.client.get(reverse("main:show_landing_page"))

    def test_has_navbar(self):
        self.assertContains(self.response, "<nav")

    def test_has_footer(self):
        self.assertContains(self.response, "<footer")

class LandingPageTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("main:show_landing_page"))

    def test_url_exists(self):
        self.assertEqual(self.response.status_code, 200)

    def test_uses_correct_template(self):
        self.assertTemplateUsed(self.response, "pages/landing_page.html")

    def test_contains_main_heading(self):
        self.assertContains(self.response, "<h1")
        self.assertContains(self.response, "Healthy Eco Foody")

class CustomUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            date_of_birth=date(2007, 4, 22),
        )

    def test_custom_user(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.date_of_birth, date(2007, 4, 22))
        self.assertTrue(self.user.check_password("securepassword123"))
        self.assertFalse(self.user.is_superuser)

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser")

    
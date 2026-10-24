from django.test import TestCase
from django.urls import reverse

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
        self.assertContains(self.response, "Healthy Eco Foody")
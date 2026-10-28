from django.test import TestCase
from django.urls import reverse


class SharedLayoutTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("main:show_landing_page"))

    def test_base_composes_header_and_footer_components(self):
        self.assertTemplateUsed(self.response, "components/header.html")
        self.assertTemplateUsed(self.response, "components/footer.html")

    def test_discover_link_is_wired_in_desktop_and_mobile_nav(self):
        self.assertContains(self.response, f'href="{reverse("main:discover")}"', count=2)

    def test_open_food_facts_attribution_is_in_footer(self):
        self.assertContains(self.response, "Open Food Facts")
        self.assertContains(self.response, "ODbL")

    def test_theme_toggle_still_rendered_in_both_navs(self):
        self.assertContains(self.response, 'class="hef-theme-toggle"', count=2)

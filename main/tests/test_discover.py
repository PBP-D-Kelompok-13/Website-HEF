from django.test import TestCase
from django.urls import reverse
from main.models import Bookmark
from .factories import make_product, make_user

HTMX = {"HTTP_HX_REQUEST": "true"}
OOB_TOAST = 'hx-swap-oob="beforeend"'


class DiscoverPageTests(TestCase):
    url = reverse("main:discover")

    def test_full_page_uses_templates_and_first_page_only(self):
        for _ in range(8):
            make_product()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "pages/discover.html")
        self.assertTemplateUsed(r, "partials/discover_shelf.html")
        self.assertContains(r, "8 products")
        self.assertContains(r, "You've explored 6 of 8 products")
        self.assertContains(r, "Load more products")

    def test_empty_shelf_and_filtered_empty_states(self):
        r_empty = self.client.get(self.url)
        self.assertContains(r_empty, "The shelf is empty. Scan a barcode to add your first product.")
        r_search = self.client.get(self.url, {"q": "nonexistent"})
        self.assertContains(r_search, "No products match your search.")

    def test_card_shows_scores_mobile_grid_and_detail_link(self):
        p = make_product(name="Oat Milk Zed", eco_grade="a", nutri_grade="")
        r = self.client.get(self.url)
        self.assertContains(r, reverse("main:product_detail", args=[p.barcode]))
        self.assertContains(r, "col-6 col-lg-4")
        self.assertContains(r, "hef-score-a")
        self.assertContains(r, "hef-score-na")
        self.assertContains(r, "CO₂ data unavailable")

    def test_search_form_is_wired_for_htmx(self):
        r = self.client.get(self.url)
        self.assertContains(r, f'hx-get="{self.url}"')
        self.assertContains(r, 'hx-target="#discover-results"')
        self.assertContains(r, 'hx-push-url="true"')

    def test_pills_reflect_the_querystring(self):
        r = self.client.get(self.url, {"category": "Snacks", "eco": "a"})
        self.assertContains(r, 'value="Snacks" checked')
        self.assertContains(r, 'value="a" checked')

    def test_barcode_like_query_without_match_offers_import(self):
        r = self.client.get(self.url, {"q": "3017620422003"})
        self.assertContains(r, reverse("main:lookup_product", args=["3017620422003"]))

    def test_short_number_does_not_offer_import(self):
        r = self.client.get(self.url, {"q": "1234"})
        self.assertNotContains(r, "Import barcode")

    def test_saved_pill_and_add_button_are_login_only(self):
        self.assertNotContains(self.client.get(self.url), 'name="saved"')
        self.assertNotContains(self.client.get(self.url), reverse("main:product_create"))
        self.client.force_login(make_user())
        self.assertContains(self.client.get(self.url), 'name="saved"')
        self.assertContains(self.client.get(self.url), reverse("main:product_create"))


class DiscoverFilterTests(TestCase):
    url = reverse("main:discover")

    def names(self, response):
        return [p.name for p in response.context["page_obj"]]

    def test_database_filters(self):
        make_product(name="Bev Alpha", category="Beverages", eco_grade="a", nutri_grade="a")
        make_product(name="Snack Beta", category="Snacks", eco_grade="e", nutri_grade="d")
        cases = [
            ({"q": "alpha"}, ["Bev Alpha"]),
            ({"category": "Snacks"}, ["Snack Beta"]),
            ({"eco": "a"}, ["Bev Alpha"]),
            ({"nutri": "d"}, ["Snack Beta"]),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(self.names(self.client.get(self.url, params)), expected)

    def test_sort_options(self):
        make_product(name="Zed", eco_grade="e")
        make_product(name="Alpha", eco_grade="a")
        self.assertEqual(self.names(self.client.get(self.url, {"sort": "name"})), ["Alpha", "Zed"])
        self.assertEqual(self.names(self.client.get(self.url, {"sort": "eco"})), ["Alpha", "Zed"])

    def test_saved_filter_only_applies_to_logged_in_users(self):
        user = make_user()
        mine, other = make_product(name="Saved Item"), make_product(name="Other Item")
        Bookmark.objects.create(user=user, product=mine)
        anonymous = self.client.get(self.url, {"saved": "1"})
        self.assertEqual(sorted(self.names(anonymous)), ["Other Item", "Saved Item"])
        self.client.force_login(user)
        self.assertEqual(self.names(self.client.get(self.url, {"saved": "1"})), ["Saved Item"])

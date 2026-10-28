from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from main.models import Bookmark, Product
from .factories import make_product, make_user

HTMX = {"HTTP_HX_REQUEST": "true"}
OOB_TOAST = 'hx-swap-oob="beforeend"'


@patch("main.views.fetch_and_save_product")
class LookupProductTests(TestCase):
    def url(self, code):
        return reverse("main:lookup_product", args=[code])

    def test_existing_product_redirects_without_calling_the_api(self, fetch):
        p = make_product()
        self.assertRedirects(
            self.client.get(self.url(p.barcode)),
            reverse("main:product_detail", args=[p.barcode]),
            fetch_redirect_response=False,
        )
        fetch.assert_not_called()

    def test_anonymous_unknown_barcode_goes_to_login_without_api_call(self, fetch):
        r = self.client.get(self.url("3017620422003"), follow=True)
        self.assertRedirects(r, reverse("main:login_account"))
        self.assertContains(r, "Please log in to import new products.")
        fetch.assert_not_called()

    def test_logged_in_unknown_barcode_imports_for_that_user(self, fetch):
        user = make_user()
        fetch.side_effect = lambda code, user=None: make_product(barcode=code, name="Imported")
        self.client.force_login(user)
        r = self.client.get(self.url("3017620422003"), follow=True)
        fetch.assert_called_once_with("3017620422003", user=user)
        self.assertRedirects(r, reverse("main:product_detail", args=["3017620422003"]))
        self.assertContains(r, "Imported added to Discover.", count=1)

    def test_not_found_on_open_food_facts_redirects_with_error(self, fetch):
        fetch.return_value = None
        self.client.force_login(make_user())
        r = self.client.get(self.url("3017620422003"), follow=True)
        self.assertRedirects(r, reverse("main:discover"))
        self.assertContains(r, "was not found on Open Food Facts.")

    def test_invalid_barcode_never_reaches_the_api(self, fetch):
        self.client.force_login(make_user())
        r = self.client.get(self.url("abc"), follow=True)
        self.assertContains(r, "valid barcode")
        fetch.assert_not_called()


class ScanFlowTests(TestCase):
    def test_scanner_modal_exposes_lookup_url_template(self):
        r = self.client.get(reverse("main:discover"))
        expected = reverse("main:lookup_product", args=["__CODE__"])
        self.assertContains(r, f'data-lookup-url="{expected}"')
        self.assertContains(r, "discover_scanner.js")

    @patch("main.services.requests.get")
    def test_scanned_barcode_populates_discover_shelf_end_to_end(self, get):
        get.return_value.json.return_value = {
            "status": 1,
            "code": "3017624010701",
            "product": {
                "product_name": "Scanned Nutella",
                "brands": "Ferrero",
                "categories_tags": ["en:spreads"],
                "ecoscore_grade": "d",
                "nutriscore_grade": "e",
            },
        }
        self.client.force_login(make_user())
        self.client.get(reverse("main:lookup_product", args=["3017624010701"]))
        shelf = self.client.get(reverse("main:discover"))
        self.assertContains(shelf, "Scanned Nutella")
        self.assertContains(shelf, "1 product")



class ProductDetailTests(TestCase):
    def test_404_for_unknown_barcode(self):
        self.assertEqual(self.client.get(reverse("main:product_detail", args=["nope"])).status_code, 404)

    def test_scores_are_public_but_details_need_login(self):
        p = make_product(ingredients="Water, oats", co2_kg=0.45, eco_grade="a")
        r = self.client.get(reverse("main:product_detail", args=[p.barcode]))
        self.assertTemplateUsed(r, "pages/product_detail.html")
        self.assertContains(r, "hef-score-banner")
        self.assertContains(r, "Log in to see the full breakdown")
        self.assertNotContains(r, "Water, oats")
        self.assertNotContains(r, "0.45")

    def test_logged_in_user_sees_full_breakdown(self):
        p = make_product(
            ingredients="Water, oats",
            co2_kg=0.45,
            nova_group=1,
            allergens="gluten",
            origin="Local",
            sugars_100g=2.0,
            sugars_level="low",
        )
        self.client.force_login(make_user())
        r = self.client.get(reverse("main:product_detail", args=[p.barcode]))
        for text in ("Water, oats", "0.45", "Group 1 - Unprocessed", "gluten", "Local", "low"):
            self.assertContains(r, text)
        self.assertNotContains(r, "Log in to see the full breakdown")

    def test_selected_grade_is_marked_once_per_scale(self):
        p = make_product(eco_grade="a", nutri_grade="c")
        r = self.client.get(reverse("main:product_detail", args=[p.barcode]))
        self.assertContains(r, "hef-scale-item hef-score-a selected", count=1)
        self.assertContains(r, "hef-scale-item hef-score-c selected", count=1)

    def test_missing_data_uses_fallbacks(self):
        p = make_product(eco_grade="", nutri_grade="", co2_kg=None)
        self.client.force_login(make_user())
        r = self.client.get(reverse("main:product_detail", args=[p.barcode]))
        for text in (
            "N/A",
            "Not classified",
            "Ingredients list not available.",
            "None reported.",
            "Location not specified",
            "Eco-Score not available",
        ):
            self.assertContains(r, text)
        self.assertNotContains(r, " selected")

    def test_edit_and_delete_controls_only_for_owner(self):
        owner, stranger = make_user("owner"), make_user("stranger")
        p = make_product(created_by=owner)
        url = reverse("main:product_detail", args=[p.barcode])
        self.client.force_login(stranger)
        self.assertNotContains(self.client.get(url), reverse("main:product_edit", args=[p.barcode]))
        self.client.force_login(owner)
        self.assertContains(self.client.get(url), reverse("main:product_edit", args=[p.barcode]))
        self.assertContains(self.client.get(url), "deleteProductModal")

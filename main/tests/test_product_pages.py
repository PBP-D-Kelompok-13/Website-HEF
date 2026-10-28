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

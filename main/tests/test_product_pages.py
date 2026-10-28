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



class BookmarkToggleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(name="Oat Milk Zed")
        self.url = reverse("main:toggle_bookmark", args=[self.product.barcode])

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url, **HTMX).status_code, 405)

    def test_non_htmx_post_redirects_to_discover(self):
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.post(self.url),
            reverse("main:discover"),
            fetch_redirect_response=False,
        )
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_anonymous_htmx_is_sent_to_login_without_saving(self):
        r = self.client.post(self.url, **HTMX)
        self.assertEqual(r["HX-Redirect"], reverse("main:login_account"))
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_anonymous_gets_error_toast_on_login_page(self):
        self.client.post(self.url, **HTMX)
        r = self.client.get(reverse("main:login_account"))
        self.assertContains(r, "Please log in to save products.", count=1)

    def test_first_post_saves_and_returns_button_with_oob_toast(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, **HTMX)
        self.assertTrue(Bookmark.objects.filter(user=self.user, product=self.product).exists())
        self.assertTemplateUsed(r, "partials/bookmark_toggle.html")
        self.assertContains(r, "is-saved")
        self.assertContains(r, 'aria-pressed="true"')
        self.assertContains(r, OOB_TOAST, count=1)
        self.assertContains(r, "Saved Oat Milk Zed.", count=1)

    def test_second_post_removes_and_returns_unsaved_button(self):
        Bookmark.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.user)
        r = self.client.post(self.url, **HTMX)
        self.assertEqual(Bookmark.objects.count(), 0)
        self.assertNotContains(r, "is-saved")
        self.assertContains(r, 'aria-pressed="false"')
        self.assertContains(r, "Removed Oat Milk Zed from saved.", count=1)

    def test_toast_does_not_leak_to_next_page(self):
        self.client.force_login(self.user)
        self.client.post(self.url, **HTMX)
        self.assertNotContains(self.client.get(reverse("main:discover")), "Saved Oat Milk Zed.")

    def test_unknown_product_is_404(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.post(reverse("main:toggle_bookmark", args=["nope"]), **HTMX).status_code,
            404,
        )

    def test_cards_render_saved_state_for_the_current_user_only(self):
        other = make_user("other")
        Bookmark.objects.create(user=other, product=self.product)
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("main:discover")), "is-saved")
        self.client.force_login(other)
        self.assertContains(self.client.get(reverse("main:discover")), "is-saved")



VALID = {"barcode": "2000000099999", "name": "Home Granola", "category": "Breakfast"}


class ProductCreateTests(TestCase):
    url = reverse("main:product_create")

    def test_requires_login(self):
        self.assertRedirects(
            self.client.get(self.url),
            f'{reverse("main:login_account")}?next={self.url}',
        )

    def test_get_renders_form(self):
        self.client.force_login(make_user())
        r = self.client.get(self.url)
        self.assertTemplateUsed(r, "pages/product_form.html")

    def test_valid_post_creates_product_owned_by_user_with_toast(self):
        user = make_user()
        self.client.force_login(user)
        r = self.client.post(self.url, VALID, follow=True)
        product = Product.objects.get(barcode="2000000099999")
        self.assertEqual(product.created_by, user)
        self.assertRedirects(r, reverse("main:product_detail", args=[product.barcode]))
        self.assertContains(r, "Product successfully added.", count=1)

    def test_invalid_barcode_and_duplicate_are_rejected(self):
        self.client.force_login(make_user())
        r = self.client.post(self.url, {**VALID, "barcode": "12ab"})
        self.assertContains(r, "Barcode must be 8-14 digits.")
        make_product(barcode="2000000099999")
        r = self.client.post(self.url, VALID)
        self.assertEqual(Product.objects.filter(barcode="2000000099999").count(), 1)
        self.assertEqual(r.status_code, 200)

    def test_invalid_post_shows_no_toast(self):
        self.client.force_login(make_user())
        self.assertNotContains(self.client.post(self.url, {**VALID, "name": ""}), "successfully")


class ProductEditDeleteTests(TestCase):
    def setUp(self):
        self.owner, self.stranger = make_user("owner"), make_user("stranger")
        self.product = make_product(name="Old Name", created_by=self.owner)
        self.edit_url = reverse("main:product_edit", args=[self.product.barcode])
        self.delete_url = reverse("main:product_delete", args=[self.product.barcode])

    def test_owner_can_update_but_barcode_is_immutable(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            self.edit_url,
            {**VALID, "barcode": "9999999999999", "name": "New Name"},
            follow=True,
        )
        self.product.refresh_from_db()
        self.assertEqual((self.product.name, self.product.barcode), ("New Name", self.product.barcode))
        self.assertNotEqual(self.product.barcode, "9999999999999")
        self.assertContains(r, "Product successfully updated.", count=1)

    def test_stranger_cannot_edit_or_delete(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)
        self.assertEqual(self.client.post(self.edit_url, VALID).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_staff_can_edit(self):
        self.client.force_login(make_user("staffer", is_staff=True))
        self.assertEqual(self.client.get(self.edit_url).status_code, 200)

    def test_anonymous_is_redirected_to_login(self):
        self.assertEqual(self.client.get(self.edit_url).status_code, 302)
        self.assertEqual(self.client.post(self.delete_url).status_code, 302)

    def test_delete_requires_post(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.delete_url).status_code, 405)

    def test_owner_can_delete_with_toast(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.delete_url, follow=True)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertRedirects(r, reverse("main:discover"))
        self.assertContains(r, "Product successfully deleted.", count=1)

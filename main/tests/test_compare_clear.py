from django.test import Client, TestCase
from django.urls import reverse

from main.models import Product, SavedComparison
from main.tests.factories import make_product, make_user


class CompareClearTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_clear_owner")
        cls.other_user = make_user(username="compare_clear_other")

        cls.first = make_product(name="Clear Oat Drink")
        cls.second = make_product(name="Clear Soy Drink")
        cls.third = make_product(name="Clear Almond Drink")

        for user in (cls.user, cls.other_user):
            SavedComparison.objects.create(
                user=user,
                title="Perbandingan yang tetap tersimpan",
                barcodes=[cls.first.barcode, cls.second.barcode],
            )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_clear")
        self.selected = [
            self.first.barcode,
            self.second.barcode,
            self.third.barcode,
        ]
        self.set_selection(self.selected)

    def set_selection(self, barcodes, client=None):
        client = client or self.client
        session = client.session
        session["comparison_barcodes"] = list(barcodes)
        session["compare_test_marker"] = "keep"
        session.save()

    def selection(self, client=None):
        client = client or self.client
        return client.session.get("comparison_barcodes", [])

    def test_post_clears_all_selected_products(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["barcodes"], [])
        self.assertEqual(response.json()["count"], 0)
        self.assertFalse(response.json()["can_compare"])
        self.assertEqual(self.selection(), [])

    def test_htmx_clear_returns_empty_workspace_and_hides_results(self):
        before = self.client.get(
            reverse("main:show_compare"),
            {"run": "1"},
        )
        self.assertContains(before, 'id="compare-results-title"')

        response = self.client.post(
            self.url,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_workspace.html",
        )
        self.assertEqual(self.selection(), [])
        self.assertEqual(response.context["products"], [])
        self.assertEqual(response.context["slots"], [None, None, None])
        self.assertEqual(response.context["selected_count"], 0)
        self.assertFalse(response.context["can_compare"])
        self.assertFalse(response.context["show_results"])
        self.assertContains(response, "Selection cleared.")
        self.assertNotContains(response, 'id="compare-results-title"')
        self.assertNotContains(response, 'id="compare-save-open"')
        self.assertNotContains(response, "<html")
        self.assertNotIn("HX-Redirect", response.headers)

    def test_clearing_an_empty_selection_is_safe_to_repeat(self):
        self.set_selection([])

        for attempt in range(2):
            with self.subTest(attempt=attempt):
                response = self.client.post(self.url)

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["ok"])
                self.assertEqual(self.selection(), [])

    def test_clear_preserves_saved_comparisons_and_products(self):
        saved_before = list(
            SavedComparison.objects.order_by("pk").values()
        )
        products_before = list(
            Product.objects.order_by("pk").values()
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(SavedComparison.objects.order_by("pk").values()),
            saved_before,
        )
        self.assertEqual(
            list(Product.objects.order_by("pk").values()),
            products_before,
        )

    def test_clear_only_changes_current_users_selection(self):
        other_client = Client()
        other_client.force_login(self.other_user)
        other_selection = [self.first.barcode, self.second.barcode]
        self.set_selection(other_selection, client=other_client)

        response = self.client.post(
            self.url,
            {"user": self.other_user.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.selection(), [])
        self.assertEqual(
            self.selection(client=other_client),
            other_selection,
        )
        self.assertEqual(
            self.client.session["compare_test_marker"],
            "keep",
        )
        self.assertEqual(
            self.client.get(reverse("main:show_compare")).status_code,
            200,
        )

    def test_methods_other_than_post_do_not_clear_selection(self):
        for method in ("get", "put", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url)

                self.assertEqual(response.status_code, 405)
                self.assertEqual(self.selection(), self.selected)

    def test_guest_cannot_clear_selection(self):
        guest = Client()
        self.set_selection(self.selected, client=guest)

        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = guest.post(self.url, **headers)

                self.assertRedirects(
                    response,
                    f"{reverse('main:login_account')}?next={self.url}",
                    fetch_redirect_response=False,
                )
                self.assertEqual(
                    self.selection(client=guest),
                    self.selected,
                )

    def test_post_without_csrf_does_not_clear_selection(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_selection(self.selected, client=csrf_client)

        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = csrf_client.post(self.url, **headers)

                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    self.selection(client=csrf_client),
                    self.selected,
                )

    def test_post_with_valid_csrf_token_can_clear_selection(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_selection(self.selected, client=csrf_client)

        form_response = csrf_client.get(
            reverse("main:compare_save")
        )
        self.assertEqual(form_response.status_code, 200)
        token = str(form_response.context["csrf_token"])

        response = csrf_client.post(
            self.url,
            {"csrfmiddlewaretoken": token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.selection(client=csrf_client), [])
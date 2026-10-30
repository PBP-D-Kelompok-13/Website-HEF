from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape

from main.models import Product, SavedComparison
from main.tests.factories import make_product, make_user


class CompareDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_delete_owner")
        cls.other_user = make_user(username="compare_delete_other")
        cls.first = make_product(name="Delete Oat Drink")
        cls.second = make_product(name="Delete Soy Drink")
        codes = [cls.first.barcode, cls.second.barcode]
        cls.saved = SavedComparison.objects.create(
            user=cls.user, title="Comparison to delete", barcodes=codes,
        )
        cls.kept = SavedComparison.objects.create(
            user=cls.user, title="Keep this comparison", barcodes=codes,
        )
        cls.foreign = SavedComparison.objects.create(
            user=cls.other_user, title="Private comparison", barcodes=codes,
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_saved_delete", args=[self.saved.pk])
        self.active = [self.second.barcode, self.first.barcode]
        self.set_selection(self.client)

    def set_selection(self, client):
        session = client.session
        session["comparison_barcodes"] = list(self.active)
        session.save()

    def snapshot(self):
        return list(SavedComparison.objects.order_by("pk").values())

    def assert_selection_unchanged(self, client=None):
        client = client or self.client
        self.assertEqual(client.session["comparison_barcodes"], self.active)

    def test_get_shows_confirmation_without_deleting(self):
        before = self.snapshot()
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = self.client.get(self.url, **headers)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "partials/compare_delete_form.html")
                self.assertEqual(response.context["comparison"].pk, self.saved.pk)
                self.assertContains(response, self.saved.title)
                self.assertContains(response, 'method="post"')
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, 'name="confirm"')
                self.assertContains(response, 'data-bs-dismiss="modal"')
                self.assertContains(response, "Cancel")
                self.assertEqual(self.snapshot(), before)
                self.assert_selection_unchanged()

    def test_query_parameter_cannot_confirm_deletion(self):
        before = self.snapshot()
        response = self.client.get(self.url, {"confirm": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.snapshot(), before)

    def test_saved_list_offers_only_owned_delete_actions(self):
        response = self.client.get(reverse("main:compare_saved_list"))
        self.assertContains(response, f'hx-get="{self.url}"')
        foreign_url = reverse("main:compare_saved_delete", args=[self.foreign.pk])
        self.assertNotContains(response, f'hx-get="{foreign_url}"')

    def test_confirmed_post_deletes_only_target_and_preserves_products(self):
        survivors = [row for row in self.snapshot() if row["id"] != self.saved.pk]
        products_before = list(Product.objects.order_by("pk").values())
        response = self.client.post(self.url, {"confirm": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["comparison_id"], self.saved.pk)
        self.assertFalse(SavedComparison.objects.filter(pk=self.saved.pk).exists())
        self.assertEqual(self.snapshot(), survivors)
        self.assertEqual(list(Product.objects.order_by("pk").values()), products_before)
        self.assert_selection_unchanged()

    def test_missing_or_invalid_confirmation_does_not_delete(self):
        before = self.snapshot()
        for data in ({}, {"confirm": ""}, {"confirm": "no"}):
            with self.subTest(data=data):
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assertTrue(response.json()["errors"])
                self.assertEqual(self.snapshot(), before)
                self.assert_selection_unchanged()

    def test_htmx_invalid_confirmation_returns_error_without_deleting(self):
        before = self.snapshot()
        response = self.client.post(self.url, {}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/compare_delete_form.html")
        self.assertTrue(response.context["errors"])
        self.assertNotIn("HX-Trigger-After-Swap", response.headers)
        self.assertEqual(self.snapshot(), before)

    def test_htmx_success_returns_escaped_feedback(self):
        title = '<script>alert("delete")</script>'
        self.saved.title = title
        self.saved.save(update_fields=["title"])
        response = self.client.post(self.url, {"confirm": "yes"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/compare_delete_success.html")
        self.assertContains(response, escape(title))
        self.assertNotContains(response, title)
        self.assertEqual(response.headers["HX-Trigger-After-Swap"], "comparisonDeleted")
        self.assertFalse(SavedComparison.objects.filter(pk=self.saved.pk).exists())
        self.assert_selection_unchanged()

    def test_confirmation_escapes_user_title(self):
        title = '<img src=x onerror=alert(1)>'
        self.saved.title = title
        self.saved.save(update_fields=["title"])
        response = self.client.get(self.url)
        self.assertContains(response, escape(title))
        self.assertNotContains(response, title)

    def test_posted_owner_and_id_cannot_change_target(self):
        before_foreign = SavedComparison.objects.values().get(pk=self.foreign.pk)
        response = self.client.post(self.url, {
            "confirm": "yes", "comparison_id": self.foreign.pk,
            "user": self.other_user.pk, "user_id": self.other_user.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedComparison.objects.filter(pk=self.saved.pk).exists())
        self.assertEqual(SavedComparison.objects.values().get(pk=self.foreign.pk), before_foreign)
        self.assertTrue(SavedComparison.objects.filter(pk=self.kept.pk).exists())

    def test_other_users_comparison_returns_404(self):
        before = self.snapshot()
        url = reverse("main:compare_saved_delete", args=[self.foreign.pk])
        for method in ("get", "post"):
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(method=method, headers=headers):
                    response = getattr(self.client, method)(url, {"confirm": "yes"}, **headers)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotContains(response, self.foreign.title, status_code=404)
                    self.assertEqual(self.snapshot(), before)
                    self.assert_selection_unchanged()

    def test_missing_record_returns_404(self):
        before = self.snapshot()
        pk = max(self.saved.pk, self.kept.pk, self.foreign.pk) + 1000
        url = reverse("main:compare_saved_delete", args=[pk])
        for method in ("get", "post"):
            response = getattr(self.client, method)(url, {"confirm": "yes"})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(self.snapshot(), before)

    def test_guest_cannot_open_or_submit_confirmation(self):
        guest = Client()
        before = self.snapshot()

        for method in ("get", "post"):
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(method=method, headers=headers):
                    # GET hanya membuka dialog; POST mengirim konfirmasi.
                    data = {} if method == "get" else {"confirm": "yes"}

                    response = getattr(guest, method)(
                        self.url,
                        data,
                        **headers,
                    )

                    self.assertRedirects(
                        response,
                        f"{reverse('main:login_account')}?next={self.url}",
                        fetch_redirect_response=False,
                    )
                    self.assertEqual(self.snapshot(), before)

    def test_unsupported_methods_do_not_delete(self):
        before = self.snapshot()
        for method in ("put", "patch", "delete"):
            response = getattr(self.client, method)(self.url)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(self.snapshot(), before)

    def test_post_without_csrf_does_not_delete(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.set_selection(client)
        before = self.snapshot()
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            response = client.post(self.url, {"confirm": "yes"}, **headers)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.snapshot(), before)
            self.assert_selection_unchanged(client)

    def test_valid_csrf_allows_confirmed_deletion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.set_selection(client)
        form_response = client.get(self.url)
        self.assertEqual(form_response.status_code, 200)
        response = client.post(self.url, {
            "confirm": "yes",
            "csrfmiddlewaretoken": str(form_response.context["csrf_token"]),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedComparison.objects.filter(pk=self.saved.pk).exists())
        self.assert_selection_unchanged(client)

    def test_repeated_delete_does_not_affect_other_records(self):
        first = self.client.post(self.url, {"confirm": "yes"})
        self.assertEqual(first.status_code, 200)
        remaining = self.snapshot()
        second = self.client.post(self.url, {"confirm": "yes"})
        self.assertEqual(second.status_code, 404)
        self.assertEqual(self.snapshot(), remaining)
        self.assert_selection_unchanged()

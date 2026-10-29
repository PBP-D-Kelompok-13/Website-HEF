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

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class CompareAddTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="compare_actions",
            email="compare-actions@example.com",
            password="TestPassword123!",
            date_of_birth=date(2000, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_add")

    def set_selection(self, barcodes):
        session = self.client.session
        session["comparison_barcodes"] = barcodes
        session.save()

    def selection(self):
        return self.client.session.get("comparison_barcodes", [])

    def post_product(self, barcode, exists=True):
        product = SimpleNamespace(barcode=barcode) if exists else None

        with patch(
            "main.comparison_views.resolve_product",
            return_value=product,
        ):
            return self.client.post(self.url, {"barcode": barcode})

    def test_add_existing_product(self):
        self.set_selection(["001"])

        response = self.post_product("002")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.selection(), ["001", "002"])

    def test_duplicate_preserves_selection(self):
        self.set_selection(["001", "002"])

        response = self.post_product("002")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.selection(), ["001", "002"])

    def test_fourth_product_preserves_selection(self):
        self.set_selection(["001", "002", "003"])

        response = self.post_product("004")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.selection(), ["001", "002", "003"])

    def test_unknown_product_is_not_added(self):
        self.set_selection(["001"])

        response = self.post_product("999", exists=False)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.selection(), ["001"])

    def test_empty_barcode_is_rejected(self):
        self.set_selection(["001"])

        response = self.post_product("")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.selection(), ["001"])

    def test_get_does_not_change_selection(self):
        self.set_selection(["001"])

        response = self.client.get(self.url, {"barcode": "002"})

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.selection(), ["001"])

    def test_guest_cannot_add_product(self):
        self.client.logout()

        response = self.client.post(self.url, {"barcode": "001"})

        self.assertRedirects(
            response,
            f"{reverse('main:login_account')}?next={self.url}",
            fetch_redirect_response=False,
        )
        self.assertEqual(self.selection(), [])

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(self.url, {"barcode": "001"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            csrf_client.session.get("comparison_barcodes", []),
            [],
        )
        
class CompareRemoveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="compare_remove",
            email="compare-remove@example.com",
            password="TestPassword123!",
            date_of_birth=date(2000, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_remove")

        session = self.client.session
        session["comparison_barcodes"] = ["001", "002"]
        session.save()

    def selection(self):
        return self.client.session.get("comparison_barcodes", [])

    def test_remove_selected_product(self):
        response = self.client.post(self.url, {"barcode": "001"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.selection(), ["002"])
        self.assertFalse(response.json()["can_compare"])

    def test_unknown_product_leaves_selection_unchanged(self):
        response = self.client.post(self.url, {"barcode": "999"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.selection(), ["001", "002"])

    def test_missing_barcode_is_rejected(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.selection(), ["001", "002"])

    def test_get_does_not_remove_product(self):
        response = self.client.get(self.url, {"barcode": "001"})

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.selection(), ["001", "002"])

    def test_guest_cannot_remove_product(self):
        self.client.logout()

        response = self.client.post(self.url, {"barcode": "001"})

        self.assertRedirects(
            response,
            f"{reverse('main:login_account')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_post_without_csrf_does_not_remove_product(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        session = csrf_client.session
        session["comparison_barcodes"] = ["001", "002"]
        session.save()

        response = csrf_client.post(self.url, {"barcode": "001"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            csrf_client.session["comparison_barcodes"],
            ["001", "002"],
        )
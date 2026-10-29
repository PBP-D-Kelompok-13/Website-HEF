from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CompareDisplayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="compare_display",
            email="compare-display@example.com",
            password="TestPassword123!",
            date_of_birth=date(2000, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:show_compare")

        # Data contoh khusus tes, bukan produk API sungguhan.
        self.products = {
            "001": SimpleNamespace(
                barcode="001",
                name="Example Oat Drink",
                brand="Example Oat Brand",
                image_url="",
                eco_grade="a",
                nutri_grade="b",
            ),
            "002": SimpleNamespace(
                barcode="002",
                name="Example Soy Drink",
                brand="Example Soy Brand",
                image_url="",
                eco_grade="",
                nutri_grade="a",
            ),
        }

    def set_selection(self, barcodes):
        session = self.client.session
        session["comparison_barcodes"] = barcodes
        session.save()

    def get_page(self, htmx=False, run=False):
        headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}
        params = {"run": "1"} if run else {}

        with patch(
            "main.comparison_views.resolve_product",
            side_effect=lambda barcode: self.products.get(barcode),
        ):
            return self.client.get(self.url, params, **headers)

    def test_selected_products_are_displayed(self):
        self.set_selection(["001", "002"])

        response = self.get_page(run=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Example Oat Drink")
        self.assertContains(response, "Example Soy Drink")
        self.assertContains(response, "Example Oat Brand")
        self.assertContains(response, "Example Soy Brand")
        self.assertContains(response, "Eco-Score")
        self.assertContains(response, "Nutri-Score")
        self.assertContains(
            response,
            'aria-label="Eco-Score A"',
        )
        self.assertContains(
            response,
            'aria-label="Nutri-Score B"',
        )

    def test_missing_score_has_explicit_label(self):
        self.set_selection(["001", "002"])

        response = self.get_page(run=True)

        self.assertContains(
            response,
            'aria-label="Eco-Score not available"',
        )

    def test_product_name_is_escaped(self):
        self.products["001"].name = "<script>alert(1)</script>"
        self.set_selection(["001", "002"])

        response = self.get_page(run=True)

        self.assertContains(
            response,
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )
        self.assertNotContains(
            response,
            "<script>alert(1)</script>",
        )

    def test_unavailable_product_is_reported_without_changing_session(self):
        self.set_selection(["001", "999"])

        response = self.get_page()

        self.assertContains(response, "Product unavailable")
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            ["001", "999"],
        )

    def test_htmx_returns_workspace_without_full_page(self):
        self.set_selection(["001", "002"])

        response = self.get_page(htmx=True, run=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_workspace.html",
        )
        self.assertTemplateNotUsed(response, "base.html")
        self.assertContains(response, "Example Oat Drink")
        self.assertNotContains(response, "<html")
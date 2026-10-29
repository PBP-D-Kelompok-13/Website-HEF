from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from main.comparison_views import (
    ProductSourceUnavailable,
    build_comparison_context_for_barcodes,
    display_grade,
    resolve_product,
)
from main.models import SavedComparison
from main.tests.factories import make_product, make_user


class CompareEdgeCaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_edge_owner")
        cls.first = make_product(
            name="Edge Oat Drink",
            image_url="https://example.com/oat.png",
        )
        cls.second = make_product(name="Edge Soy Drink")

    def setUp(self):
        self.client.force_login(self.user)

    def set_selection(self, value):
        session = self.client.session
        session["comparison_barcodes"] = value
        session.save()

    def test_missing_product_model_reports_source_unavailable(self):
        barcode = self.first.barcode

        with patch("main.comparison_views.apps") as mocked_apps:
            mocked_apps.get_model.side_effect = LookupError(
                "Model unavailable"
            )

            with self.assertRaises(ProductSourceUnavailable):
                resolve_product(barcode)

            mocked_apps.get_model.assert_called_once_with(
                "main", "Product"
            )

    def test_add_source_failure_preserves_selection(self):
        selected = [self.first.barcode]
        self.set_selection(selected)

        with patch(
            "main.comparison_views.resolve_product",
            side_effect=ProductSourceUnavailable,
        ):
            response = self.client.post(
                reverse("main:compare_add"),
                {"barcode": self.second.barcode},
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ok"])
        self.assertTrue(response.json()["errors"])
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            selected,
        )

    def test_workspace_duplicate_returns_targeted_feedback(self):
        selected = [self.first.barcode]
        self.set_selection(selected)

        response = self.client.post(
            reverse("main:compare_add"),
            {
                "barcode": self.first.barcode,
                "source": "workspace",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_add_feedback.html",
        )
        self.assertTrue(response.context["errors"])
        self.assertEqual(
            response.headers["HX-Retarget"],
            "#compare-picker-feedback",
        )
        self.assertEqual(response.headers["HX-Reswap"], "innerHTML")
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            selected,
        )

    def test_remove_rejects_invalid_session_without_overwriting_it(self):
        invalid_selection = "not-a-list"
        self.set_selection(invalid_selection)

        response = self.client.post(
            reverse("main:compare_remove"),
            {"barcode": self.first.barcode},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertTrue(response.json()["errors"])
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            invalid_selection,
        )

    def test_non_string_scores_are_not_converted_to_grades(self):
        for value in (None, 0, False, [], {}):
            with self.subTest(value=value):
                self.assertEqual(display_grade(value), "")

        self.assertEqual(display_grade(" A "), "a")
        self.assertEqual(display_grade("unknown"), "")

    def test_unavailable_source_produces_unavailable_products(self):
        selected = [self.first.barcode, self.second.barcode]

        with patch(
            "main.comparison_views.resolve_product",
            side_effect=ProductSourceUnavailable,
        ):
            context = build_comparison_context_for_barcodes(selected)

        self.assertTrue(context["source_unavailable"])
        self.assertFalse(context["can_compare"])
        self.assertEqual(context["selected_count"], 2)
        self.assertEqual(
            [product["barcode"] for product in context["products"]],
            selected,
        )
        for product in context["products"]:
            self.assertFalse(product["available"])
            self.assertEqual(product["eco_grade"], "")
            self.assertEqual(product["nutri_grade"], "")

    def test_valid_product_image_url_is_preserved(self):
        context = build_comparison_context_for_barcodes(
            [self.first.barcode, self.second.barcode]
        )

        self.assertTrue(context["can_compare"])
        self.assertEqual(
            context["products"][0]["image_url"],
            "https://example.com/oat.png",
        )
        self.assertEqual(context["products"][1]["image_url"], "")

    def test_picker_can_return_search_results_only(self):
        response = self.client.get(
            reverse("main:compare_product_picker"),
            {"results": "1", "q": self.first.barcode},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_picker_results.html",
        )
        self.assertTemplateNotUsed(
            response,
            "partials/compare_product_picker.html",
        )
        self.assertEqual(
            [product.barcode for product in response.context["page"]],
            [self.first.barcode],
        )
        self.assertContains(response, self.first.name)
        self.assertNotContains(response, self.second.name)

    def test_saved_comparison_string_representation_is_its_title(self):
        comparison = SavedComparison(
            user=self.user,
            title="My breakfast comparison",
            barcodes=[self.first.barcode, self.second.barcode],
        )

        comparison.full_clean()

        self.assertEqual(str(comparison), "My breakfast comparison")
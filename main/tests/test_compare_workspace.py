from django.test import TestCase
from django.urls import reverse

from main.tests.factories import make_product, make_user


class CompareWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_workspace")
        cls.first = make_product(name="Workspace Product One")
        cls.second = make_product(name="Workspace Product Two")

    def setUp(self):
        self.client.force_login(self.user)
        self.page_url = reverse("main:show_compare")
        self.remove_url = reverse("main:compare_remove")

    def select_products(self, *products):
        session = self.client.session
        session["comparison_barcodes"] = [
            product.barcode for product in products
        ]
        session.save()

    def test_empty_workspace_has_three_slots_linking_to_discover(self):
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-compare-slot", count=3)
        self.assertContains(
            response,
            f'hx-get="{reverse("main:compare_product_picker")}"',
            count=3,
        )
        self.assertContains(
            response,
            'data-bs-target="#compareProductPicker"',
            count=3,
        )
        self.assertEqual(
            self.client.session.get("comparison_barcodes", []),
            [],
        )

    def test_two_products_leave_one_empty_slot(self):
        self.select_products(self.first, self.second)

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-compare-slot", count=3)
        self.assertContains(response, self.first.name)
        self.assertContains(response, self.second.name)
        self.assertContains(
            response,
            f'hx-get="{reverse("main:compare_product_picker")}"',
            count=1,
        )
        self.assertContains(
            response,
            'data-bs-target="#compareProductPicker"',
            count=1,
        )
        self.assertContains(
            response,
            f'hx-post="{self.remove_url}"',
            count=2,
        )

    def test_remove_button_has_product_identity_and_accessible_label(self):
        self.select_products(self.first)

        response = self.client.get(self.page_url)

        self.assertContains(
            response,
            '<input type="hidden" name="barcode" '
            f'value="{self.first.barcode}">',
            html=True,
        )
        self.assertContains(
            response,
            f'aria-label="Remove {self.first.name}"',
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(
            response,
            'hx-target="#compare-workspace"',
        )

    def test_htmx_remove_returns_updated_workspace(self):
        self.select_products(self.first, self.second)

        response = self.client.post(
            self.remove_url,
            {"barcode": self.first.barcode},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.second.barcode],
        )
        self.assertTemplateUsed(
            response,
            "partials/compare_workspace.html",
        )
        self.assertNotContains(response, "<html")
        self.assertNotContains(response, self.first.name)
        self.assertContains(response, self.second.name)
        self.assertContains(response, "data-compare-slot", count=3)
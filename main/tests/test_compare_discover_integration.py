from django.test import TestCase
from django.urls import reverse

from main.tests.factories import make_product, make_user


class CompareDiscoverIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_integration")
        cls.product = make_product(name="Integration Oat Drink")

    def setUp(self):
        self.client.force_login(self.user)
        self.add_url = reverse("main:compare_add")
        self.detail_url = reverse(
            "main:product_detail",
            kwargs={"barcode": self.product.barcode},
        )

    def test_detail_offers_htmx_add_to_compare(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'hx-post="{self.add_url}"',
        )
        self.assertContains(
            response,
            'hx-target="#compare-add-feedback"',
        )
        self.assertContains(
            response,
            (
                '<input type="hidden" name="barcode" '
                f'value="{self.product.barcode}">'
            ),
            html=True,
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, "Add to Compare")

    def test_htmx_add_saves_real_product_and_opens_compare(self):
        response = self.client.post(
            self.add_url,
            {"barcode": self.product.barcode},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.product.barcode],
        )
        self.assertEqual(
            response.headers.get("HX-Redirect"),
            reverse("main:show_compare"),
        )

    def test_htmx_duplicate_shows_error_without_changing_selection(self):
        session = self.client.session
        session["comparison_barcodes"] = [self.product.barcode]
        session.save()

        response = self.client.post(
            self.add_url,
            {"barcode": self.product.barcode},
            HTTP_HX_REQUEST="true",
        )

        # HTML pesan validasi ditampilkan langsung oleh HTMX.
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["Content-Type"].startswith("text/html")
        )
        self.assertContains(response, 'role="alert"')
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.product.barcode],
        )

    def test_guest_does_not_get_add_form(self):
        self.client.logout()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            f'hx-post="{self.add_url}"',
        )
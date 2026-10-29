from django.test import TestCase
from django.urls import reverse

from main.tests.factories import make_product, make_user


class ComparePickerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_picker")
        cls.first = make_product(name="Picker Oat Drink")
        cls.second = make_product(name="Picker Soy Drink")

    def setUp(self):
        self.client.force_login(self.user)
        self.picker_url = reverse("main:compare_product_picker")

        session = self.client.session
        session["comparison_barcodes"] = [self.first.barcode]
        session.save()

    def get_picker(self, query=""):
        return self.client.get(
            self.picker_url,
            {"q": query},
            HTTP_HX_REQUEST="true",
        )

    def test_picker_returns_search_and_product_choices(self):
        response = self.get_picker()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_product_picker.html",
        )
        self.assertContains(response, "Choose a product")
        self.assertContains(response, 'name="q"')
        self.assertContains(response, self.second.name)
        self.assertContains(
            response,
            f'hx-post="{reverse("main:compare_add")}"',
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertNotContains(response, "<html")

    def test_search_finds_product_by_name_or_barcode(self):
        for query in ("Soy", self.second.barcode):
            with self.subTest(query=query):
                response = self.get_picker(query)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, self.second.name)
                self.assertNotContains(response, self.first.name)

    def test_selected_product_is_excluded_without_changing_selection(self):
        response = self.get_picker()

        self.assertContains(response, self.second.name)
        self.assertNotContains(response, self.first.name)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.first.barcode],
        )

    def test_empty_search_result_has_clear_message(self):
        response = self.get_picker("no-product-matches-this-query")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No products found.")
        self.assertNotContains(response, self.second.name)

    def test_product_name_is_escaped_in_picker(self):
        self.second.name = "<script>alert(1)</script>"
        self.second.save(update_fields=["name"])

        response = self.get_picker()

        self.assertContains(
            response,
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_guest_cannot_access_picker(self):
        self.client.logout()

        response = self.get_picker()

        self.assertRedirects(
            response,
            f"{reverse('main:login_account')}?next={self.picker_url}?q=",
            fetch_redirect_response=False,
        )

    def test_selecting_from_workspace_updates_slots_without_redirect(self):
        response = self.client.post(
            reverse("main:compare_add"),
            {
                "barcode": self.second.barcode,
                "source": "workspace",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertTemplateUsed(
            response,
            "partials/compare_workspace.html",
        )
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.first.barcode, self.second.barcode],
        )
        self.assertContains(response, self.first.name)
        self.assertContains(response, self.second.name)
        self.assertContains(response, "Ready when you are")
        self.assertNotContains(response, 'id="compare-results-title"')
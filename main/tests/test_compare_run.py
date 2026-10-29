from django.test import TestCase
from django.urls import reverse

from main.tests.factories import make_product, make_user


class CompareRunTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_run")
        cls.first = make_product(
            name="Run Product One",
            eco_grade="a",
            nutri_grade="b",
        )
        cls.second = make_product(
            name="Run Product Two",
            eco_grade="c",
            nutri_grade="",
        )
        cls.third = make_product(name="Run Product Three")
        cls.fourth = make_product(name="Run Product Four")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:show_compare")
        self.choose(self.first.barcode, self.second.barcode)

    def choose(self, *barcodes):
        session = self.client.session
        session["comparison_barcodes"] = list(barcodes)
        session.save()

    def test_scores_are_hidden_before_compare_is_requested(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.first.name)
        self.assertContains(response, self.second.name)
        self.assertContains(response, "Ready when you are")
        self.assertContains(response, "Compare products")
        self.assertNotContains(response, 'id="compare-results-title"')
        self.assertNotContains(response, 'aria-label="Eco-Score A"')

    def test_explicit_compare_shows_scores_without_changing_selection(self):
        before = self.client.session["comparison_barcodes"]

        response = self.client.get(self.url, {"run": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="compare-results-title"')
        self.assertContains(response, 'aria-label="Eco-Score A"')
        self.assertContains(response, 'aria-label="Eco-Score C"')
        self.assertContains(response, 'aria-label="Nutri-Score not available"')
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            before,
        )

    def test_invalid_selection_cannot_show_results(self):
        invalid_selections = [
            [],
            [self.first.barcode],
            [self.first.barcode, self.first.barcode],
            [
                self.first.barcode,
                self.second.barcode,
                self.third.barcode,
                self.fourth.barcode,
            ],
        ]

        for barcodes in invalid_selections:
            with self.subTest(barcodes=barcodes):
                self.choose(*barcodes)

                response = self.client.get(self.url, {"run": "1"})

                self.assertEqual(response.status_code, 400)
                self.assertNotContains(
                    response,
                    'id="compare-results-title"',
                    status_code=400,
                )
                self.assertEqual(
                    self.client.session["comparison_barcodes"],
                    barcodes,
                )

    def test_htmx_compare_returns_only_workspace(self):
        response = self.client.get(
            self.url,
            {"run": "1"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_workspace.html",
        )
        self.assertContains(response, 'id="compare-results-title"')
        self.assertNotContains(response, "<html")

    def test_removing_product_hides_previous_results(self):
        self.choose(
            self.first.barcode,
            self.second.barcode,
            self.third.barcode,
        )
        comparison = self.client.get(self.url, {"run": "1"})
        self.assertContains(comparison, 'id="compare-results-title"')

        response = self.client.post(
            reverse("main:compare_remove"),
            {"barcode": self.third.barcode},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            [self.first.barcode, self.second.barcode],
        )
        self.assertContains(response, "Ready when you are")
        self.assertNotContains(response, 'id="compare-results-title"')
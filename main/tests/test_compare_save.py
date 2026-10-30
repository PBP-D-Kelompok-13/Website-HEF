from django.test import Client, TestCase
from django.urls import reverse

from main.models import SavedComparison
from main.tests.factories import make_product, make_user


class CompareSaveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_save_owner")
        cls.other_user = make_user(username="compare_save_other")

        cls.first = make_product(name="Save Oat Drink")
        cls.second = make_product(name="Save Soy Drink")
        cls.third = make_product(name="Save Almond Drink")
        cls.fourth = make_product(name="Save Rice Drink")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_save")

        # Urutan sengaja berbeda dari urutan pembuatan produk.
        self.selected = [
            self.second.barcode,
            self.first.barcode,
        ]
        self.set_selection(self.selected)

    def set_selection(self, barcodes, client=None):
        client = client if client is not None else self.client

        session = client.session
        session["comparison_barcodes"] = barcodes
        session.save()

    def test_opening_save_form_does_not_create_comparison(self):
        response = self.client.get(
            self.url,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_save_form.html",
        )
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertEqual(SavedComparison.objects.count(), 0)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            self.selected,
        )

    def test_save_two_or_three_products_preserves_owner_and_order(self):
        selections = (
            self.selected,
            self.selected + [self.third.barcode],
        )

        for barcodes in selections:
            with self.subTest(barcodes=barcodes):
                self.set_selection(barcodes)
                count_before = SavedComparison.objects.count()

                response = self.client.post(
                    self.url,
                    {"title": "  Pilihan susu nabati  "},
                )

                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.json()["ok"])

                saved = SavedComparison.objects.get(
                    pk=response.json()["comparison_id"],
                )

                self.assertEqual(
                    SavedComparison.objects.count(),
                    count_before + 1,
                )
                self.assertEqual(saved.user_id, self.user.pk)
                self.assertEqual(saved.title, "Pilihan susu nabati")
                self.assertEqual(saved.barcodes, barcodes)
                self.assertIsNotNone(saved.created_at)
                self.assertEqual(
                    self.client.session["comparison_barcodes"],
                    barcodes,
                )

    def test_invalid_title_does_not_create_comparison(self):
        for title in ("", "   ", "A" * 121):
            with self.subTest(title=title):
                response = self.client.post(
                    self.url,
                    {"title": title},
                )

                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assertIn("title", response.json()["errors"])
                self.assertEqual(SavedComparison.objects.count(), 0)
                self.assertEqual(
                    self.client.session["comparison_barcodes"],
                    self.selected,
                )

    def test_title_of_120_characters_is_accepted(self):
        response = self.client.post(
            self.url,
            {"title": "A" * 120},
        )

        self.assertEqual(response.status_code, 201)
        saved = SavedComparison.objects.get()
        self.assertEqual(saved.title, "A" * 120)

    def test_invalid_selection_does_not_create_comparison(self):
        invalid_selections = (
            [],
            [self.first.barcode],
            [self.first.barcode, self.first.barcode],
            [
                self.first.barcode,
                self.second.barcode,
                self.third.barcode,
                self.fourth.barcode,
            ],
            [self.first.barcode, ""],
            [self.first.barcode, "unknown-product"],
            [self.first.barcode, 123],
            None,
        )

        for barcodes in invalid_selections:
            with self.subTest(barcodes=barcodes):
                self.set_selection(barcodes)

                response = self.client.post(
                    self.url,
                    {"title": "Pilihan tidak valid"},
                )

                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assertEqual(SavedComparison.objects.count(), 0)
                self.assertEqual(
                    self.client.session["comparison_barcodes"],
                    barcodes,
                )

    def test_post_cannot_override_owner_or_session_products(self):
        response = self.client.post(
            self.url,
            {
                "title": "Perbandingan milikku",
                "user": self.other_user.pk,
                "barcodes": [
                    self.third.barcode,
                    self.fourth.barcode,
                ],
            },
        )

        self.assertEqual(response.status_code, 201)

        saved = SavedComparison.objects.get()

        self.assertEqual(saved.user_id, self.user.pk)
        self.assertEqual(saved.barcodes, self.selected)
        self.assertFalse(
            SavedComparison.objects.filter(
                user=self.other_user,
            ).exists()
        )

    def test_guest_cannot_open_form_or_save(self):
        self.client.logout()

        for method in ("get", "post"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url,
                    {"title": "Guest comparison"},
                )

                # POST tidak memiliki query string pada URL.
                # GET diuji terpisah tanpa data agar URL redirect jelas.
                if method == "get":
                    response = self.client.get(self.url)

                self.assertRedirects(
                    response,
                    f"{reverse('main:login_account')}?next={self.url}",
                    fetch_redirect_response=False,
                )
                self.assertEqual(SavedComparison.objects.count(), 0)

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_selection(self.selected, client=csrf_client)

        response = csrf_client.post(
            self.url,
            {"title": "Tanpa token"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SavedComparison.objects.count(), 0)
        self.assertEqual(
            csrf_client.session["comparison_barcodes"],
            self.selected,
        )

    def test_post_with_valid_csrf_token_can_save(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_selection(self.selected, client=csrf_client)

        form_response = csrf_client.get(
            self.url,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(form_response.status_code, 200)

        token = csrf_client.cookies["csrftoken"].value

        response = csrf_client.post(
            self.url,
            {"title": "Dengan token"},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SavedComparison.objects.count(), 1)
        self.assertEqual(
            SavedComparison.objects.get().user_id,
            self.user.pk,
        )

    def test_htmx_save_returns_escaped_success_feedback(self):
        title = "<script>alert(1)</script>"

        response = self.client.post(
            self.url,
            {"title": title},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_save_success.html",
        )
        self.assertContains(
            response,
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )
        self.assertNotContains(response, title)
        self.assertNotContains(response, "<html")
        self.assertEqual(
            response.headers.get("HX-Trigger-After-Swap"),
            "comparisonSaved",
        )
        self.assertEqual(SavedComparison.objects.count(), 1)
        self.assertEqual(SavedComparison.objects.get().title, title)

    def test_htmx_invalid_title_returns_form_without_saving(self):
        response = self.client.post(
            self.url,
            {"title": "   "},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_save_form.html",
        )
        self.assertIn("title", response.context["form"].errors)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertNotIn("HX-Trigger-After-Swap", response.headers)
        self.assertEqual(SavedComparison.objects.count(), 0)

    def test_missing_scores_do_not_prevent_saving(self):
        self.second.eco_grade = ""
        self.second.nutri_grade = ""
        self.second.save(
            update_fields=["eco_grade", "nutri_grade"],
        )

        response = self.client.post(
            self.url,
            {"title": "Produk dengan skor belum tersedia"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            SavedComparison.objects.get().barcodes,
            self.selected,
        )

        self.second.refresh_from_db()
        self.assertEqual(self.second.eco_grade, "")
        self.assertEqual(self.second.nutri_grade, "")

    def test_put_does_not_create_comparison(self):
        response = self.client.put(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(SavedComparison.objects.count(), 0)
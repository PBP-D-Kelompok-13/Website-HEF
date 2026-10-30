from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from main.models import SavedComparison
from main.tests.factories import make_product, make_user


class CompareSavedReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="saved_reader")
        cls.other_user = make_user(username="saved_other")

        cls.first = make_product(
            name="Read Oat Drink",
            eco_grade="a",
            nutri_grade="b",
        )
        cls.second = make_product(
            name="Read Soy Drink",
            eco_grade="c",
            nutri_grade="d",
        )
        cls.third = make_product(name="Read Almond Drink")

        cls.own_two = SavedComparison.objects.create(
            user=cls.user,
            title="Susu untuk sarapan",
            barcodes=[
                cls.second.barcode,
                cls.first.barcode,
            ],
        )

        cls.own_three = SavedComparison.objects.create(
            user=cls.user,
            title="Pilihan camilan",
            barcodes=[
                cls.first.barcode,
                cls.second.barcode,
                cls.third.barcode,
            ],
        )

        cls.foreign = SavedComparison.objects.create(
            user=cls.other_user,
            title="Susu rahasia pengguna lain",
            barcodes=[
                cls.first.barcode,
                cls.second.barcode,
                cls.third.barcode,
            ],
        )

    def setUp(self):
        self.client.force_login(self.user)

        self.list_url = reverse("main:compare_saved_list")
        self.detail_url = reverse(
            "main:compare_saved_detail",
            args=[self.own_two.pk],
        )

        # Pilihan aktif berbeda dari perbandingan yang akan dibuka.
        self.current_selection = [
            self.first.barcode,
            self.third.barcode,
        ]

        session = self.client.session
        session["comparison_barcodes"] = self.current_selection
        session.save()

    def test_compare_page_links_to_saved_comparisons(self):
        response = self.client.get(reverse("main:show_compare"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{self.list_url}"',
        )

    def test_list_only_shows_current_users_comparisons(self):
        response = self.client.get(
            self.list_url,
            {"user": self.other_user.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "pages/compare_saved.html",
        )
        self.assertContains(response, self.own_two.title)
        self.assertContains(response, self.own_three.title)
        self.assertNotContains(response, self.foreign.title)

        self.assertContains(
            response,
            f'href="{self.detail_url}"',
        )

        foreign_url = reverse(
            "main:compare_saved_detail",
            args=[self.foreign.pk],
        )
        self.assertNotContains(
            response,
            f'href="{foreign_url}"',
        )

    def test_search_filters_titles_within_current_users_records(self):
        response = self.client.get(
            self.list_url,
            {"q": "  SUSU  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.own_two.title)
        self.assertNotContains(response, self.own_three.title)
        self.assertNotContains(response, self.foreign.title)

    def test_product_count_filter(self):
        cases = (
            ("2", self.own_two, self.own_three),
            ("3", self.own_three, self.own_two),
        )

        for count, included, excluded in cases:
            with self.subTest(count=count):
                response = self.client.get(
                    self.list_url,
                    {"count": count},
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, included.title)
                self.assertNotContains(response, excluded.title)
                self.assertNotContains(response, self.foreign.title)

    def test_all_or_unknown_count_keeps_owned_records_visible(self):
        for count in ("all", "invalid"):
            with self.subTest(count=count):
                response = self.client.get(
                    self.list_url,
                    {"count": count},
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, self.own_two.title)
                self.assertContains(response, self.own_three.title)
                self.assertNotContains(response, self.foreign.title)

    def test_search_and_count_filter_work_together_without_leaking_records(self):
        response = self.client.get(
            self.list_url,
            {"q": "Susu", "count": "3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No comparisons match your search.",
        )
        self.assertNotContains(response, self.own_two.title)
        self.assertNotContains(response, self.own_three.title)
        self.assertNotContains(response, self.foreign.title)

    def test_user_without_saved_records_sees_empty_state(self):
        SavedComparison.objects.filter(user=self.user).delete()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No saved comparisons yet")
        self.assertNotContains(response, self.foreign.title)

    def test_htmx_search_returns_only_owned_results_fragment(self):
        response = self.client.get(
            self.list_url,
            {"q": "Susu"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_saved_results.html",
        )
        self.assertContains(response, self.own_two.title)
        self.assertNotContains(response, self.own_three.title)
        self.assertNotContains(response, self.foreign.title)
        self.assertNotContains(response, "<html")

    def test_owner_can_open_detail_with_saved_product_order(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "pages/compare_saved_detail.html",
        )
        self.assertEqual(
            response.context["comparison"].pk,
            self.own_two.pk,
        )
        self.assertEqual(
            [
                product["barcode"]
                for product in response.context["products"]
            ],
            self.own_two.barcodes,
        )

        self.assertContains(response, self.own_two.title)
        self.assertContains(response, self.first.name)
        self.assertContains(response, self.second.name)
        self.assertNotContains(response, self.third.name)
        self.assertContains(response, "Eco-Score")
        self.assertContains(response, "Nutri-Score")
        self.assertContains(response, f'href="{self.list_url}"')

    def test_other_users_detail_returns_404_for_normal_and_htmx_requests(self):
        foreign_url = reverse(
            "main:compare_saved_detail",
            args=[self.foreign.pk],
        )

        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = self.client.get(
                    foreign_url,
                    {"user": self.other_user.pk},
                    **headers,
                )

                self.assertEqual(response.status_code, 404)
                self.assertNotContains(
                    response,
                    self.foreign.title,
                    status_code=404,
                )

    def test_nonexistent_detail_returns_404(self):
        missing_url = reverse(
            "main:compare_saved_detail",
            args=[self.foreign.pk + 1000],
        )

        response = self.client.get(missing_url)

        self.assertEqual(response.status_code, 404)

    def test_guest_cannot_read_list_or_detail(self):
        self.client.logout()

        for url in (self.list_url, self.detail_url):
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(url=url, headers=headers):
                    response = self.client.get(url, **headers)

                    self.assertRedirects(
                        response,
                        f"{reverse('main:login_account')}?next={url}",
                        fetch_redirect_response=False,
                    )

    def test_reading_does_not_change_saved_records_or_active_selection(self):
        before = list(
            SavedComparison.objects.order_by("pk").values(
                "pk",
                "user_id",
                "title",
                "barcodes",
                "created_at",
                "updated_at",
            )
        )

        for url in (self.list_url, self.detail_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        after = list(
            SavedComparison.objects.order_by("pk").values(
                "pk",
                "user_id",
                "title",
                "barcodes",
                "created_at",
                "updated_at",
            )
        )

        self.assertEqual(after, before)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            self.current_selection,
        )

    def test_post_to_read_endpoints_is_rejected(self):
        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                response = self.client.post(
                    url,
                    {"title": "Unexpected change"},
                )

                self.assertEqual(response.status_code, 405)

        self.own_two.refresh_from_db()
        self.assertEqual(self.own_two.title, "Susu untuk sarapan")
        self.assertEqual(SavedComparison.objects.count(), 3)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            self.current_selection,
        )

    def test_titles_and_product_names_are_escaped(self):
        dangerous_title = "<script>alert(1)</script>"
        dangerous_product = '<img src=x onerror="alert(2)">'

        self.own_two.title = dangerous_title
        self.own_two.save(update_fields=["title"])

        self.first.name = dangerous_product
        self.first.save(update_fields=["name"])

        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(dangerous_title))
                self.assertContains(response, escape(dangerous_product))
                self.assertNotContains(response, dangerous_title)
                self.assertNotContains(response, dangerous_product)

    def test_missing_scores_are_reported_in_detail(self):
        self.first.eco_grade = ""
        self.first.nutri_grade = ""
        self.first.save(
            update_fields=["eco_grade", "nutri_grade"],
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not available")

        products = {
            product["barcode"]: product
            for product in response.context["products"]
        }
        self.assertEqual(products[self.first.barcode]["eco_grade"], "")
        self.assertEqual(products[self.first.barcode]["nutri_grade"], "")

    def test_deleted_product_does_not_break_list_or_detail(self):
        original_barcodes = list(self.own_two.barcodes)
        self.second.delete()

        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Product unavailable")

        self.own_two.refresh_from_db()
        self.assertEqual(self.own_two.barcodes, original_barcodes)
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            self.current_selection,
        )

    def test_detail_uses_latest_shared_product_scores(self):
        self.first.eco_grade = "e"
        self.first.save(update_fields=["eco_grade"])

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        products = {
            product["barcode"]: product
            for product in response.context["products"]
        }

        self.assertEqual(
            products[self.first.barcode]["eco_grade"],
            "e",
        )
        self.assertContains(response, 'aria-label="Eco-Score E"')
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape

from main.models import SavedComparison
from main.tests.factories import make_product, make_user


class CompareEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="compare_edit_owner")
        cls.other_user = make_user(username="compare_edit_other")

        cls.first = make_product(name="Edit Oat Drink")
        cls.second = make_product(name="Edit Soy Drink")
        cls.third = make_product(name="Edit Almond Drink")
        cls.fourth = make_product(name="Edit Rice Drink")

        cls.saved = SavedComparison.objects.create(
            user=cls.user,
            title="Pilihan awal",
            barcodes=[cls.second.barcode, cls.first.barcode],
        )
        cls.foreign = SavedComparison.objects.create(
            user=cls.other_user,
            title="Perbandingan pribadi pengguna lain",
            barcodes=[cls.first.barcode, cls.third.barcode],
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("main:compare_saved_edit", args=[self.saved.pk])
        self.active_selection = [self.fourth.barcode, self.third.barcode]
        self.set_active_selection(self.client)

    def set_active_selection(self, client):
        session = client.session
        session["comparison_barcodes"] = list(self.active_selection)
        session.save()

    def payload(self, **overrides):
        data = {
            "title": "Pilihan baru",
            "barcodes": [self.first.barcode, self.third.barcode],
        }
        data.update(overrides)
        return data

    def snapshot(self):
        return list(
            SavedComparison.objects.order_by("pk").values(
                "pk", "user_id", "title", "barcodes",
                "created_at", "updated_at",
            )
        )

    def assert_active_selection_unchanged(self):
        self.assertEqual(
            self.client.session["comparison_barcodes"],
            self.active_selection,
        )

    def test_get_prefills_form_without_changing_data(self):
        before = self.snapshot()

        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = self.client.get(self.url, **headers)

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    "partials/compare_edit_form.html",
                )
                self.assertEqual(
                    response.context["comparison"].pk,
                    self.saved.pk,
                )
                self.assertEqual(
                    response.context["form"]["title"].value(),
                    self.saved.title,
                )
                self.assertEqual(
                    [p["barcode"] for p in response.context["products"]],
                    self.saved.barcodes,
                )
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, 'name="barcodes"')
                self.assertEqual(self.snapshot(), before)
                self.assert_active_selection_unchanged()

    def test_saved_list_offers_owned_edit_action(self):
        response = self.client.get(reverse("main:compare_saved_list"))
        foreign_url = reverse(
            "main:compare_saved_edit",
            args=[self.foreign.pk],
        )

        self.assertContains(response, f'hx-get="{self.url}"')
        self.assertNotContains(response, f'hx-get="{foreign_url}"')

    def test_owner_updates_title_and_ordered_products_on_same_record(self):
        created_at = self.saved.created_at

        for barcodes in (
            [self.third.barcode, self.first.barcode],
            [self.fourth.barcode, self.second.barcode, self.third.barcode],
        ):
            with self.subTest(barcodes=barcodes):
                response = self.client.post(
                    self.url,
                    self.payload(title="  Pilihan baru  ", barcodes=barcodes),
                )

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["ok"])
                self.assertEqual(
                    response.json()["comparison_id"],
                    self.saved.pk,
                )
                self.saved.refresh_from_db()
                self.assertEqual(self.saved.title, "Pilihan baru")
                self.assertEqual(self.saved.barcodes, barcodes)
                self.assertEqual(self.saved.user_id, self.user.pk)
                self.assertEqual(self.saved.created_at, created_at)
                self.assertEqual(SavedComparison.objects.count(), 2)
                self.assert_active_selection_unchanged()

    def test_posted_owner_and_id_cannot_change_target(self):
        foreign_before = SavedComparison.objects.values().get(
            pk=self.foreign.pk
        )

        response = self.client.post(
            self.url,
            self.payload(
                user=self.other_user.pk,
                user_id=self.other_user.pk,
                comparison_id=self.foreign.pk,
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["comparison_id"], self.saved.pk)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.user_id, self.user.pk)
        self.assertEqual(self.saved.title, "Pilihan baru")
        self.assertEqual(
            SavedComparison.objects.values().get(pk=self.foreign.pk),
            foreign_before,
        )
        self.assertEqual(SavedComparison.objects.count(), 2)

    def test_invalid_title_leaves_saved_data_unchanged(self):
        before = self.snapshot()

        for title in ("", "   ", "A" * 121):
            with self.subTest(title=title):
                response = self.client.post(
                    self.url,
                    self.payload(title=title),
                )

                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assertIn("title", response.json()["errors"])
                self.assertEqual(self.snapshot(), before)
                self.assert_active_selection_unchanged()

    def test_invalid_products_leave_saved_data_unchanged(self):
        before = self.snapshot()

        for barcodes in (
            [],
            [self.first.barcode],
            [self.first.barcode, self.first.barcode],
            [
                self.first.barcode, self.second.barcode,
                self.third.barcode, self.fourth.barcode,
            ],
            [self.first.barcode, ""],
            [self.first.barcode, "not-a-registered-product"],
        ):
            with self.subTest(barcodes=barcodes):
                response = self.client.post(
                    self.url,
                    self.payload(barcodes=barcodes),
                )

                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assertTrue(response.json()["errors"])
                self.assertEqual(self.snapshot(), before)
                self.assert_active_selection_unchanged()

    def test_missing_scores_do_not_prevent_editing(self):
        self.third.eco_grade = ""
        self.third.nutri_grade = ""
        self.third.save(update_fields=["eco_grade", "nutri_grade"])

        response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 200)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.barcodes, self.payload()["barcodes"])
        self.third.refresh_from_db()
        self.assertEqual(self.third.eco_grade, "")
        self.assertEqual(self.third.nutri_grade, "")

    def test_htmx_success_returns_escaped_feedback(self):
        title = "<script>alert(1)</script>"

        response = self.client.post(
            self.url,
            self.payload(title=title),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_edit_success.html",
        )
        self.assertContains(response, escape(title))
        self.assertNotContains(response, title)
        self.assertEqual(
            response.headers.get("HX-Trigger-After-Swap"),
            "comparisonUpdated",
        )
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.title, title)
        self.assertEqual(self.saved.barcodes, self.payload()["barcodes"])
        self.assert_active_selection_unchanged()

    def test_htmx_invalid_form_preserves_draft_and_saved_data(self):
        before = self.snapshot()

        response = self.client.post(
            self.url,
            self.payload(title=""),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/compare_edit_form.html",
        )
        self.assertTrue(response.context["form"].is_bound)
        self.assertIn("title", response.context["form"].errors)
        self.assertEqual(
            [p["barcode"] for p in response.context["products"]],
            self.payload()["barcodes"],
        )
        self.assertNotIn("HX-Trigger-After-Swap", response.headers)
        self.assertEqual(self.snapshot(), before)
        self.assert_active_selection_unchanged()

    def test_existing_title_and_product_name_are_escaped(self):
        title = "<script>alert(1)</script>"
        name = "<img src=x onerror=alert(1)>"
        self.saved.title = title
        self.saved.save(update_fields=["title"])
        self.first.name = name
        self.first.save(update_fields=["name"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, escape(title))
        self.assertContains(response, escape(name))
        self.assertNotContains(response, title)
        self.assertNotContains(response, name)

    def test_other_users_record_returns_404_without_changes(self):
        url = reverse(
            "main:compare_saved_edit",
            args=[self.foreign.pk],
        )
        before = self.snapshot()

        for method in ("get", "post"):
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(method=method, headers=headers):
                    response = getattr(self.client, method)(
                        url,
                        self.payload(),
                        **headers,
                    )

                    self.assertEqual(response.status_code, 404)
                    self.assertNotContains(
                        response,
                        self.foreign.title,
                        status_code=404,
                    )
                    self.assertEqual(self.snapshot(), before)
                    self.assert_active_selection_unchanged()

    def test_missing_record_returns_404(self):
        missing_pk = max(self.saved.pk, self.foreign.pk) + 1000
        url = reverse("main:compare_saved_edit", args=[missing_pk])
        before = self.snapshot()

        for method in ("get", "post"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    url,
                    self.payload(),
                )

                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.snapshot(), before)

    def test_guest_cannot_open_or_submit_edit_form(self):
        guest = Client()
        before = self.snapshot()

        for method in ("get", "post"):
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(method=method, headers=headers):
                    response = getattr(guest, method)(
                        self.url,
                        **headers,
                    )

                    self.assertRedirects(
                        response,
                        f"{reverse('main:login_account')}?next={self.url}",
                        fetch_redirect_response=False,
                    )
                    self.assertEqual(self.snapshot(), before)

    def test_unsupported_methods_do_not_change_saved_data(self):
        before = self.snapshot()

        for method in ("put", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url)

                self.assertEqual(response.status_code, 405)
                self.assertEqual(self.snapshot(), before)
                self.assert_active_selection_unchanged()

    def test_post_without_csrf_does_not_update_comparison(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_active_selection(csrf_client)
        before = self.snapshot()

        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            with self.subTest(headers=headers):
                response = csrf_client.post(
                    self.url,
                    self.payload(),
                    **headers,
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(
                    csrf_client.session["comparison_barcodes"],
                    self.active_selection,
                )

    def test_post_with_valid_csrf_can_update_comparison(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.set_active_selection(csrf_client)
        form_response = csrf_client.get(self.url)
        self.assertEqual(form_response.status_code, 200)
        token = str(form_response.context["csrf_token"])

        response = csrf_client.post(
            self.url,
            self.payload(csrfmiddlewaretoken=token),
        )

        self.assertEqual(response.status_code, 200)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.title, "Pilihan baru")
        self.assertEqual(self.saved.barcodes, self.payload()["barcodes"])
        self.assertEqual(
            csrf_client.session["comparison_barcodes"],
            self.active_selection,
        )

    def test_deleted_product_can_be_replaced(self):
        self.first.delete()
        before = self.snapshot()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product unavailable")
        self.assertEqual(self.snapshot(), before)

        barcodes = [self.third.barcode, self.second.barcode]
        response = self.client.post(
            self.url,
            self.payload(barcodes=barcodes),
        )

        self.assertEqual(response.status_code, 200)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.barcodes, barcodes)
        self.assertEqual(SavedComparison.objects.count(), 2)
        self.assert_active_selection_unchanged()
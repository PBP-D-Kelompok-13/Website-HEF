from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
HTMX = {"HTTP_HX_REQUEST": "true"}
OOB_TOAST = 'hx-swap-oob="beforeend"'


class ToastTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.landing_url = reverse("main:show_landing_page")
        self.profile_url = reverse("main:show_profile_page")


class RedirectToastTests(ToastTestBase):
    """Full-page flows: message is queued, redirect happens, base.html renders it."""

    def test_login_shows_toast(self):
        response = self.client.post(
            reverse("main:login_account"),
            {"username": "healthyuser", "password": "StrongPass123!"},
            follow=True,
        )
        self.assertContains(response, "Login successful.", count=1)
        self.assertContains(response, "hef-toast-item")

    def test_success_toast_has_check_icon(self):
        response = self.client.post(
            reverse("main:login_account"),
            {"username": "healthyuser", "password": "StrongPass123!"},
            follow=True,
        )
        self.assertContains(response, "hef-toast-icon", count=1)

    def test_failed_login_shows_no_toast(self):
        response = self.client.post(
            reverse("main:login_account"),
            {"username": "healthyuser", "password": "wrong"},
        )
        self.assertNotContains(response, "Login successful.")

    def test_logout_shows_toast(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("main:logout_account"), follow=True)
        self.assertContains(response, "Logout successful.", count=1)

    def test_delete_account_shows_toast(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("main:delete_account"), follow=True)
        self.assertContains(response, "Account successfully deleted.", count=1)

    def test_toast_is_shown_only_once(self):
        self.client.post(
            reverse("main:login_account"),
            {"username": "healthyuser", "password": "StrongPass123!"},
        )
        self.client.get(self.landing_url)  # first page load consumes it
        response = self.client.get(self.landing_url)
        self.assertNotContains(response, "Login successful.")

    def test_registration_shows_toast_on_login_page(self):
        response = self.client.post(
            reverse("main:register_account"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "date_of_birth": "2000-05-20",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=True,
        )
        self.assertTemplateUsed(response, "pages/login.html")
        self.assertContains(response, "Account successfully registered. Please log in.", count=1)
        self.assertContains(response, "hef-toast-item")

    def test_invalid_registration_shows_no_toast(self):
        response = self.client.post(
            reverse("main:register_account"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "date_of_birth": "2000-05-20",
                "password1": "StrongPass123!",
                "password2": "DifferentPass123!",
            },
        )
        self.assertNotContains(response, "Account successfully registered. Please log in.")


class HtmxToastTests(ToastTestBase):
    """HTMX flows: the toast travels as an out-of-band fragment."""
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.edit_url = reverse("main:edit_profile_details")
        self.password_url = reverse("main:change_password")
        self.profile_data = {
            "username": "newname",
            "email": "new@example.com",
            "date_of_birth": "1999-12-31",
        }
        self.password_data = {
            "old_password": "StrongPass123!",
            "new_password1": "AnotherStrongPass456!",
            "new_password2": "AnotherStrongPass456!",
        }

    def test_profile_save_returns_oob_toast(self):
        response = self.client.post(self.edit_url, self.profile_data, **HTMX)
        self.assertContains(response, OOB_TOAST, count=1)
        self.assertContains(response, 'id="toast-container"', count=1)
        self.assertContains(response, "Account information successfully updated.", count=1)

    def test_invalid_profile_save_returns_no_toast(self):
        response = self.client.post(
            self.edit_url, {**self.profile_data, "username": ""}, **HTMX
        )
        self.assertNotContains(response, "toast-container")
        self.assertNotContains(response, "Account information successfully updated.")

    def test_cancel_returns_no_toast(self):
        response = self.client.get(reverse("main:show_profile_details"), **HTMX)
        self.assertNotContains(response, "toast-container")

    def test_htmx_toast_is_consumed_and_does_not_leak_to_next_page(self):
        self.client.post(self.edit_url, self.profile_data, **HTMX)
        response = self.client.get(self.profile_url)
        self.assertNotContains(response, "Account information successfully updated.")

    def test_password_change_returns_oob_toast(self):
        response = self.client.post(self.password_url, self.password_data, **HTMX)
        self.assertContains(response, OOB_TOAST, count=1)
        self.assertContains(response, "Password successfully changed.", count=1)

    def test_invalid_password_change_returns_no_toast(self):
        response = self.client.post(
            self.password_url,
            {**self.password_data, "old_password": "WrongPassword123!"},
            **HTMX,
        )
        self.assertNotContains(response, "toast-container")
        self.assertNotContains(response, "Password successfully changed.")
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.test import Client

from main.forms import CustomAuthenticationForm, CustomUserCreationForm

User = get_user_model()
HTMX = {"HTTP_HX_REQUEST": "true"}

class SitePageTests(TestCase):
    def test_landing_page_renders_shared_layout_and_content(self):
        response = self.client.get(reverse("main:show_landing_page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/landing_page.html")
        self.assertContains(response, "<nav")
        self.assertContains(response, "<footer")
        self.assertContains(response, "Healthy Eco Foody")
        self.assertContains(response, reverse("main:login_account"))
        self.assertContains(response, reverse("main:register_account"))


class CustomUserModelTests(TestCase):
    def test_user_fields_password_and_string_representation(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            date_of_birth=date(2007, 4, 22),
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.date_of_birth, date(2007, 4, 22))
        self.assertTrue(user.check_password("securepassword123"))
        self.assertFalse(user.is_superuser)
        self.assertEqual(str(user), "testuser")


class AuthenticationFormTests(TestCase):
    def test_registration_form_fields_styling(self):
        form = CustomUserCreationForm()

        self.assertEqual(
            list(form.fields),
            ["username", "email", "date_of_birth", "password1", "password2"],
        )
        self.assertEqual(form.fields["password2"].label, "Confirm Password")
        self.assertEqual(form.fields["date_of_birth"].label, "Date of Birth")
        self.assertEqual(form.fields["date_of_birth"].widget.input_type, "date")
        for name in form.fields:
            self.assertEqual(form.fields[name].widget.attrs["class"], "hef-input")
        self.assertEqual(
            form.fields["email"].widget.attrs["placeholder"], "Enter your email"
        )

    def test_registration_form_accepts_valid_data(self):
        form = CustomUserCreationForm(data={
            "username": "newuser",
            "email": "new@example.com",
            "date_of_birth": "2000-05-20",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_registration_form_rejects_missing_fields_and_mismatched_passwords(self):
        form = CustomUserCreationForm(data={
            "username": "newuser",
            "email": "new@example.com",
            "password1": "StrongPass123!",
            "password2": "DifferentPass123!",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("date_of_birth", form.errors)
        self.assertIn("password2", form.errors)

    def test_registration_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existing",
            email="taken@example.com",
            date_of_birth=date(1995, 1, 1),
            password="Password123!",
        )
        form = CustomUserCreationForm(data={
            "username": "newuser",
            "email": "taken@example.com",
            "date_of_birth": "2000-05-20",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_login_form_styling_and_autofocus(self):
        form = CustomAuthenticationForm()

        self.assertNotIn("autofocus", form.fields["username"].widget.attrs)
        self.assertEqual(form.fields["username"].widget.attrs["class"], "hef-input")
        self.assertEqual(
            form.fields["username"].widget.attrs["placeholder"], "Enter your Username"
        )
        self.assertEqual(
            form.fields["password"].widget.attrs["placeholder"], "Enter your password"
        )

    def test_login_form_validates_credentials(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            date_of_birth=date(1995, 1, 1),
            password="Password123!",
        )
        request = self.client.request().wsgi_request
        form = CustomAuthenticationForm(request, data={
            "username": "existing",
            "password": "Password123!",
        })

        self.assertTrue(form.is_valid(), form.errors)


class FormFieldIdTests(TestCase):
    def test_registration_form_uses_default_ids(self):
        form = CustomUserCreationForm()
        self.assertEqual(form["username"].id_for_label, "id_username")
        self.assertEqual(form["email"].id_for_label, "id_email")
        self.assertEqual(form["date_of_birth"].id_for_label, "id_date_of_birth")
        self.assertEqual(form["password1"].id_for_label, "id_password1")
        self.assertEqual(form["password2"].id_for_label, "id_password2")

    def test_login_form_uses_default_ids(self):
        form = CustomAuthenticationForm()
        self.assertEqual(form["username"].id_for_label, "id_username")
        self.assertEqual(form["password"].id_for_label, "id_password")


class LoginPageTests(TestCase):
    def setUp(self):
        self.url = reverse("main:login_account")
        self.user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            date_of_birth=date(1995, 1, 1),
            password="Password123!",
        )

    def test_get_renders_dedicated_page_and_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/login.html")
        self.assertContains(response, 'id="login-form"')
        self.assertContains(response, 'href="/static/css/auth.css"')
        self.assertIsInstance(response.context["form"], CustomAuthenticationForm)

    def test_invalid_post_renders_page_with_non_field_error(self):
        response = self.client.post(self.url, {
            "username": "existinguser",
            "password": "WrongPassword",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/login.html")
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_successful_post_logs_in_and_redirects_to_landing(self):
        response = self.client.post(self.url, {
            "username": "existinguser",
            "password": "Password123!",
        })

        self.assertRedirects(response, reverse("main:show_landing_page"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_is_redirected_from_login_page(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("main:show_landing_page"))


class RegistrationPageTests(TestCase):
    def setUp(self):
        self.url = reverse("main:register_account")
        self.valid_registration = {
            "username": "newuser",
            "email": "new@example.com",
            "date_of_birth": "2000-05-20",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        self.user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            date_of_birth=date(1995, 1, 1),
            password="Password123!",
        )

    def test_get_renders_dedicated_page_and_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/register.html")
        self.assertContains(response, 'id="register-form"')
        self.assertContains(response, 'href="/static/css/auth.css"')
        self.assertIsInstance(response.context["form"], CustomUserCreationForm)

    def test_invalid_post_renders_page_with_field_errors(self):
        response = self.client.post(self.url, {
            **self.valid_registration,
            "password2": "DifferentPass123!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/register.html")
        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_successful_post_creates_user_and_redirects_to_login(self):
        response = self.client.post(self.url, self.valid_registration)

        self.assertRedirects(response, reverse("main:login_account"))
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_authenticated_user_is_redirected_from_registration_page(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("main:show_landing_page"))

class NavbarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.url = reverse("main:show_landing_page")

    # --- Anonymous visitors: desktop + mobile ---
    def test_anonymous_navbar_shows_login_link_twice(self):
        response = self.client.get(self.url)
        self.assertContains(response, "login-link", count=2)

    def test_anonymous_navbar_hides_profile_link(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "hef-profile-link")
        self.assertNotContains(response, "hef-navbar-username")

    # --- Logged-in users: desktop + mobile ---
    def test_authenticated_navbar_shows_profile_link_twice(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "hef-profile-link", count=2)

    def test_authenticated_navbar_shows_username_twice(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "hef-navbar-username", count=2)
        self.assertContains(response, "healthyuser")

    def test_authenticated_navbar_hides_login_link(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "login-link")

class NavbarProfileLinkTests(TestCase):
    def test_profile_link_points_to_profile_page_on_both_navbars(self):
        user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.client.force_login(user)
        response = self.client.get(reverse("main:show_landing_page"))
        profile_url = reverse("main:show_profile_page")
        self.assertContains(response, f'href="{profile_url}"', count=2)

class ProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.url = reverse("main:show_profile_page")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('main:login_account')}?next={self.url}",
        )

    def test_authenticated_user_can_open_profile_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/profile_page.html")

    def test_profile_page_shows_user_details(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Your Profile")
        self.assertContains(response, "healthyuser")
        self.assertContains(response, "healthy@example.com")
        self.assertContains(response, "01/01/2000")

    def test_profile_page_shows_placeholder_cards(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Product Search History")
        self.assertContains(response, "Your Pantry")
        self.assertContains(response, "Saved Recipes")

    def test_profile_page_never_shows_password_hash(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.user.password)

class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.url = reverse("main:logout_account")

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_post_logs_out_and_redirects_to_landing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("main:show_landing_page"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_profile_page_has_logout_form_with_csrf_token(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("main:show_profile_page"))
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "Logout")

class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="StrongPass123!",
            date_of_birth=date(1999, 5, 5),
        )
        self.url = reverse("main:delete_account")

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_anonymous_post_is_redirected_to_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(
            response,
            f"{reverse('main:login_account')}?next={self.url}",
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_post_deletes_account_and_redirects_to_landing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("main:show_landing_page"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_post_only_deletes_the_logged_in_user(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertTrue(User.objects.filter(pk=self.other_user.pk).exists())

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_profile_page_has_delete_button_modal_and_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("main:show_profile_page"))
        self.assertContains(response, "Delete Account")
        self.assertContains(response, 'data-bs-target="#deleteAccountModal"')
        self.assertContains(response, 'id="deleteAccountModal"', count=1)
        self.assertContains(response, "Are you sure you want to delete your account?")
        self.assertContains(response, "Yes, I am sure")
        self.assertContains(response, "No, take me back!")
        self.assertContains(response, f'action="{self.url}"')

class ProfileEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="StrongPass123!",
            date_of_birth=date(1999, 5, 5),
        )
        self.edit_url = reverse("main:edit_profile_details")
        self.details_url = reverse("main:show_profile_details")
        self.profile_url = reverse("main:show_profile_page")
        self.valid_data = {
            "username": "newname",
            "email": "new@example.com",
            "date_of_birth": "1999-12-31",
        }

    # --- Access ---
    def test_anonymous_get_is_redirected_to_login(self):
        response = self.client.get(self.edit_url)
        self.assertRedirects(
            response, f"{reverse('main:login_account')}?next={self.edit_url}"
        )

    def test_anonymous_post_is_redirected_and_changes_nothing(self):
        response = self.client.post(self.edit_url, self.valid_data)
        self.assertRedirects(
            response, f"{reverse('main:login_account')}?next={self.edit_url}"
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "healthyuser")

    # --- Edit form (pencil) ---
    def test_get_edit_returns_form_with_current_values(self):
        self.client.force_login(self.user)
        response = self.client.get(self.edit_url, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/profile_details_edit.html")
        self.assertContains(response, 'value="healthyuser"')
        self.assertContains(response, 'value="healthy@example.com"')
        self.assertContains(response, 'value="2000-01-01"')
        self.assertContains(response, f'hx-post="{self.edit_url}"')
        self.assertContains(response, f'hx-get="{self.details_url}"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "Save")
        self.assertContains(response, "Cancel")

    def test_get_edit_without_htmx_redirects_to_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.edit_url)
        self.assertRedirects(response, self.profile_url)

    # --- Read-only version (Cancel) ---
    def test_get_details_returns_read_only_fragment(self):
        self.client.force_login(self.user)
        response = self.client.get(self.details_url, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/profile_details.html")
        self.assertContains(response, "healthyuser")
        self.assertContains(response, "healthy@example.com")
        self.assertContains(response, "01/01/2000")
        self.assertContains(response, f'hx-get="{self.edit_url}"')
        self.assertNotContains(response, "<form")

    def test_get_details_without_htmx_redirects_to_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.details_url)
        self.assertRedirects(response, self.profile_url)

    # --- Saving ---
    def test_valid_post_saves_and_returns_read_only_fragment(self):
        self.client.force_login(self.user)
        response = self.client.post(self.edit_url, self.valid_data, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/profile_details.html")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newname")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.date_of_birth, date(1999, 12, 31))
        self.assertContains(response, "newname")
        self.assertContains(response, "31/12/1999")
        self.assertNotContains(response, "<form")

    def test_valid_post_updates_navbar_name_out_of_band(self):
        self.client.force_login(self.user)
        response = self.client.post(self.edit_url, self.valid_data, **HTMX)
        self.assertContains(response, 'hx-swap-oob="true"', count=2)
        self.assertContains(response, 'id="navbar-name-desktop"')
        self.assertContains(response, 'id="navbar-name-mobile"')

    def test_post_without_changes_is_valid(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.edit_url,
            {
                "username": "healthyuser",
                "email": "healthy@example.com",
                "date_of_birth": "2000-01-01",
            },
            **HTMX,
        )
        self.assertTemplateUsed(response, "partials/profile_details.html")

    # --- Validation errors ---
    def test_post_with_taken_username_shows_error_and_saves_nothing(self):
        self.client.force_login(self.user)
        data = {**self.valid_data, "username": "otheruser"}
        response = self.client.post(self.edit_url, data, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/profile_details_edit.html")
        self.assertIn("username", response.context["form"].errors)
        self.assertNotContains(response, "hx-swap-oob")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "healthyuser")
        self.assertEqual(self.user.email, "healthy@example.com")

    def test_post_with_taken_email_shows_error_and_saves_nothing(self):
        self.client.force_login(self.user)
        data = {**self.valid_data, "email": "other@example.com"}
        response = self.client.post(self.edit_url, data, **HTMX)
        self.assertTemplateUsed(response, "partials/profile_details_edit.html")
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "healthyuser")
        self.assertEqual(self.user.email, "healthy@example.com")

    def test_post_with_missing_date_of_birth_shows_error(self):
        self.client.force_login(self.user)
        data = {**self.valid_data, "date_of_birth": ""}
        response = self.client.post(self.edit_url, data, **HTMX)
        self.assertTemplateUsed(response, "partials/profile_details_edit.html")
        self.assertIn("date_of_birth", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.date_of_birth, date(2000, 1, 1))

    # --- Security ---
    def test_post_ignores_fields_that_are_not_in_the_form(self):
        self.client.force_login(self.user)
        data = {**self.valid_data, "is_staff": "on", "is_superuser": "on"}
        self.client.post(self.edit_url, data, **HTMX)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_post_without_htmx_header_redirects_and_saves_nothing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.edit_url, self.valid_data)
        self.assertRedirects(response, self.profile_url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "healthyuser")

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(self.edit_url, self.valid_data, **HTMX)
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "healthyuser")


class ProfileEditHooksTests(TestCase):
    """The pieces of existing pages that the edit feature plugs into."""
    def setUp(self):
        self.user = User.objects.create_user(
            username="healthyuser",
            email="healthy@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
        )
        self.client.force_login(self.user)

    def test_profile_page_has_edit_container_pencil_and_htmx(self):
        response = self.client.get(reverse("main:show_profile_page"))
        edit_url = reverse("main:edit_profile_details")
        self.assertTemplateUsed(response, "partials/profile_details.html")
        self.assertContains(response, 'id="profile-details"', count=1)
        self.assertContains(response, f'hx-get="{edit_url}"')
        self.assertContains(response, 'hx-target="#profile-details"')
        self.assertContains(response, "htmx.org")

    def test_navbar_username_spans_have_ids_for_updates(self):
        response = self.client.get(reverse("main:show_landing_page"))
        self.assertContains(response, 'id="navbar-name-desktop"', count=1)
        self.assertContains(response, 'id="navbar-name-mobile"', count=1)
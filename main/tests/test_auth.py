from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from main.forms import CustomAuthenticationForm, CustomUserCreationForm, ReactivationForm

User = get_user_model()
HTMX = {"HTTP_HX_REQUEST": "true"}

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

class ReactivationFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
            is_active=False,
        )

    def test_form_fields_are_styled(self):
        form = ReactivationForm()

        self.assertEqual(list(form.fields), ["email", "password"])
        for field in form.fields.values():
            self.assertEqual(field.widget.attrs["class"], "hef-input")

    def test_valid_credentials_for_inactive_account_are_accepted(self):
        form = ReactivationForm(data={
            "email": "inactive@example.com",
            "password": "StrongPass123!",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.user.pk, self.user.pk)

    def test_unknown_email_and_wrong_password_get_the_same_generic_error(self):
        wrong_password_form = ReactivationForm(data={
            "email": "inactive@example.com",
            "password": "WrongPassword123!",
        })
        unknown_email_form = ReactivationForm(data={
            "email": "unknown@example.com",
            "password": "StrongPass123!",
        })

        self.assertFalse(wrong_password_form.is_valid())
        self.assertFalse(unknown_email_form.is_valid())

        wrong_password_error = str(wrong_password_form.non_field_errors()[0])
        unknown_email_error = str(unknown_email_form.non_field_errors()[0])
        self.assertEqual(wrong_password_error, unknown_email_error)

    def test_active_account_cannot_be_reactivated(self):
        self.user.is_active = True
        self.user.save()

        form = ReactivationForm(data={
            "email": "inactive@example.com",
            "password": "StrongPass123!",
        })

        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())


class ReactivationPageTests(TestCase):
    def setUp(self):
        self.url = reverse("main:reactivate_account")
        self.user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="StrongPass123!",
            date_of_birth=date(2000, 1, 1),
            is_active=False,
        )
        self.valid_data = {
            "email": "inactive@example.com",
            "password": "StrongPass123!",
        }

    def test_registration_page_links_to_reactivation(self):
        response = self.client.get(reverse("main:register_account"))

        self.assertContains(response, self.url)
        self.assertContains(response, "Reactivate your account")

    def test_get_renders_reactivation_form_and_csrf_token(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/reactivate_account.html")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_reactivates_existing_account_and_redirects_to_login(self):
        original_user_id = self.user.pk

        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, reverse("main:login_account"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.pk, original_user_id)
        self.assertEqual(self.user.username, "inactiveuser")
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_does_not_reactivate_account(self):
        response = self.client.post(
            self.url,
            {**self.valid_data, "password": "WrongPassword123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/reactivate_account.html")
        self.assertContains(response, "Email or password is incorrect")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_unknown_email_does_not_create_or_reactivate_an_account(self):
        response = self.client.post(
            self.url,
            {
                "email": "unknown@example.com",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email or password is incorrect")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(User.objects.count(), 1)

    def test_active_account_is_not_reactivated(self):
        self.user.is_active = True
        self.user.save()

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email or password is incorrect")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(User.objects.count(), 1)

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_authenticated_user_is_redirected_from_reactivation_page(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("main:show_landing_page"))
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from main.forms import *
from main.models import *

User = get_user_model()


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
    def test_registration_form_fields_styling_ids_and_labels(self):
        form = CustomUserCreationForm()

        self.assertEqual(
            list(form.fields),
            ["username", "email", "date_of_birth", "password1", "password2"],
        )
        self.assertEqual(form["username"].id_for_label, "register_username")
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

    def test_login_form_styling_ids_and_autofocus(self):
        form = CustomAuthenticationForm()

        self.assertEqual(form["username"].id_for_label, "login_username")
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

class PantryFeatureAcceptanceTest(TestCase):
    def test_user_pantry_management_journey(self):
        user = User.objects.create_user(
            username="celine",
            email="celine@example.com",
            date_of_birth=date(2005, 1, 1),
            password="Password123!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("main:show_inventory"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/inventory.html")

        response = self.client.post(reverse("main:add_ingredient"), {
            "name": "Broccoli",
            "category": "Vegetables",
            "quantity": "2 pcs",
            "expiration_date": "2026-11-05"
        })
        self.assertRedirects(response, reverse("main:show_inventory"))
        self.assertEqual(Ingredient.objects.count(), 1)
        
        response = self.client.get(reverse("main:show_inventory"))
        self.assertContains(response, "Broccoli")
        
class IngredientModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="celine",
            email="celine@example.com",
            date_of_birth=date(2005, 1, 1),
            password="Password123!"
        )

    def test_ingredient_creation_and_string_representation(self):
        ingredient = Ingredient.objects.create(
            user=self.user,
            name="Milk",
            category="Dairy & Eggs",
            quantity="1 bottle",
            expiration_date=date(2026, 11, 2)
        )
        self.assertEqual(ingredient.name, "Milk")
        self.assertEqual(ingredient.category, "Dairy & Eggs")
        self.assertEqual(str(ingredient), "Milk (celine)")
        
class IngredientFormTests(TestCase):
    def test_ingredient_form_accepts_valid_category_choices(self):
        form_data = {
            "name": "Apples",
            "category": "Fruits",
            "quantity": "1 kg",
            "expiration_date": "2026-11-10"
        }
        form = IngredientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_ingredient_form_rejects_invalid_category(self):
        form_data = {
            "name": "Unknown Item",
            "category": "InvalidCategory",
            "quantity": "1",
            "expiration_date": "2026-11-10"
        }
        form = IngredientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)
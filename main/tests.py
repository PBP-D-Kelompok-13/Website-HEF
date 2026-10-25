from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date 
from main.forms import CustomUserCreationForm
from main.models import CustomUser

# Uses the correct user model from AUTH_USER_MODEL
User = get_user_model()

class BaseTemplateTests(TestCase):
    # Testing untuk base.html yang dilakukan melalui loading homepage
    def setUp(self):
        self.response = self.client.get(reverse("main:show_landing_page"))

    def test_has_navbar(self):
        self.assertContains(self.response, "<nav")

    def test_has_footer(self):
        self.assertContains(self.response, "<footer")

class LandingPageTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("main:show_landing_page"))

    def test_url_exists(self):
        self.assertEqual(self.response.status_code, 200)

    def test_uses_correct_template(self):
        self.assertTemplateUsed(self.response, "pages/landing_page.html")

    def test_contains_main_heading(self):
        self.assertContains(self.response, "<h1")
        self.assertContains(self.response, "Healthy Eco Foody")

class CustomUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            date_of_birth=date(2007, 4, 22),
        )

    def test_custom_user(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.date_of_birth, date(2007, 4, 22))
        self.assertTrue(self.user.check_password("securepassword123"))
        self.assertFalse(self.user.is_superuser)

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser")

class CustomUserCreationFormTest(TestCase):
    def test_form_has_custom_fields(self):
        form = CustomUserCreationForm()
        expected_fields = ['username', 'email', 'date_of_birth']
        
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_form_valid_data(self):
        form = CustomUserCreationForm(data={
            'username': 'johndoe',
            'email': 'john@example.com',
            'date_of_birth': '1995-05-15',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })
        self.assertTrue(form.is_valid())

    def test_form_missing_date_of_birth(self):
        form = CustomUserCreationForm(data={
            'username': 'johndoe',
            'email': 'john@example.com',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)

class RegisterAndLoginHTMXTest(TestCase):
    def setUp(self):
        # Create a test user for login tests
        self.user = CustomUser.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            date_of_birth='1995-01-01',
            password='Password123!'
        )

    # --- REGISTER TESTS ---
    def test_register_htmx_invalid_post_returns_422(self):
        response = self.client.post(
            reverse('main:register_account'),
            {'username': ''},  # Missing required fields
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(response.status_code, 422)
        self.assertTemplateUsed(response, 'modals/register.html')

    def test_register_htmx_successful_post_returns_hx_redirect(self):
        response = self.client.post(
            reverse('main:register_account'),
            {
                'username': 'newuser',
                'email': 'new@example.com',
                'date_of_birth': '2000-05-20',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(CustomUser.objects.count(), 2)
        self.assertIn('HX-Redirect', response.headers)

    # --- LOGIN TESTS ---
    def test_login_htmx_invalid_post_returns_422(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'existinguser',
                'password': 'WrongPassword',
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(response.status_code, 422)
        self.assertTemplateUsed(response, 'modals/login.html')

    def test_login_htmx_successful_post_authenticates(self):
        response = self.client.post(
            reverse('main:login_account'),
            {
                'username': 'existinguser',
                'password': 'Password123!',
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(response.status_code, 204)
        self.assertIn('HX-Redirect', response.headers)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
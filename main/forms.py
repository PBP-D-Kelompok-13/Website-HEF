from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from .models import CustomUser
from django.core.exceptions import ValidationError

def style(field, placeholder):
    field.widget.attrs.update({'class': 'hef-input', 'placeholder': placeholder})

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'date_of_birth')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields['username'], 'Enter your Username')
        style(self.fields['email'], 'Enter your email')
        style(self.fields['password1'], 'Enter your password')
        style(self.fields['password2'], 'Enter your password')
        style(self.fields['date_of_birth'], 'DD/MM/YYYY')
        self.fields['password2'].label = 'Confirm Password'
        self.fields['date_of_birth'].label = 'Date of Birth'

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields['username'], 'Enter your Username')
        style(self.fields['password'], 'Enter your password')
        # Keep focus on the page heading until the user chooses a field.
        self.fields['username'].widget.attrs.pop('autofocus', None)

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields['old_password'], 'Enter your current password')
        style(self.fields['new_password1'], 'Enter your new password')
        style(self.fields['new_password2'], 'Confirm your new password')

class ProfileDetailsForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email", "date_of_birth")
        widgets = {
            "date_of_birth": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields["username"], "Enter your Username")
        style(self.fields["email"], "Enter your email")
        style(self.fields["date_of_birth"], "DD/MM/YYYY")
        self.fields["date_of_birth"].label = "Date of Birth"

class ReactivationForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )

    error_message = "Email or password is incorrect, or this account cannot be reactivated."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields["email"], "Enter the email for your account")
        style(self.fields["password"], "Enter your password")
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = CustomUser.objects.filter(email__iexact=email).first()

            if user is None or user.is_active or not user.check_password(password):
                raise ValidationError(self.error_message)

            self.user = user

        return cleaned_data


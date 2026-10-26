from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

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
        style(self.fields['username'], 'Enter your Username')
        style(self.fields['email'], 'Enter your email')
        style(self.fields['password1'], 'Enter your password')
        style(self.fields['password2'], 'Enter your password')
        style(self.fields['date_of_birth'], 'DD/MM/YYYY')
        self.fields['password2'].label = 'Confirm Password'
        self.fields['date_of_birth'].label = 'Date of Birth'

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        style(self.fields['username'], 'Enter your Username')
        style(self.fields['password'], 'Enter your password')
        # Keep focus on the page heading until the user chooses a field.
        self.fields['username'].widget.attrs.pop('autofocus', None)

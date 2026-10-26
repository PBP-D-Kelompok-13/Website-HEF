from django.urls import path
from .views import show_landing_page, register_account, login_account, show_profile_page, logout_account

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
    path('register/', register_account, name='register_account'),
    path('login/', login_account, name='login_account'),
    path("profile/", show_profile_page, name="show_profile_page"),
    path("logout/", logout_account, name="logout_account")
]
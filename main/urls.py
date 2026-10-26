from django.urls import path
from .views import *

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
    path('register/', register_account, name='register_account'),
    path('login/', login_account, name='login_account'),
    path("profile/", show_profile_page, name="show_profile_page"),
    path("logout/", logout_account, name="logout_account"),
    path("profile/delete/", delete_account, name="delete_account"),
    path("profile/details/", show_profile_details, name="show_profile_details"),
    path("profile/edit/", edit_profile_details, name="edit_profile_details"),
    path("profile/change-password/", change_password, name="change_password"),
]
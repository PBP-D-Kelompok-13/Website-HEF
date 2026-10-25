from django.urls import path
from .views import show_landing_page, register_account, login_account

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
    path('register/', register_account, name='register_account'),
    path('login/', login_account, name='login_account'),
]
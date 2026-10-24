from django.urls import path
from .views import show_landing_page

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
]
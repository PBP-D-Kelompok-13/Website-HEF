from django.urls import path
from .views import *

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
    path('register/', register_account, name='register_account'),
    path('login/', login_account, name='login_account'),
    path('pantry/', show_inventory, name='show_inventory'),
    path('pantry/add/', add_ingredient, name='add_ingredient'),
    path('pantry/edit/<int:pk>/', edit_ingredient, name='edit_ingredient'),
    path('pantry/delete/<int:pk>/', delete_ingredient, name='delete_ingredient'),
]
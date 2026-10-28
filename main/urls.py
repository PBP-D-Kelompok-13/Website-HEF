from django.urls import path
from .views import *

app_name = "main"

urlpatterns = [
    path("", show_landing_page, name="show_landing_page"),
    path("recipes/", recipe_discover, name="recipe_discover"),
    path("recipes/ingredient-suggestions/", recipe_ingredient_suggestions, name="recipe_ingredient_suggestions"),
    path("recipes/saved/", recipe_list, name="recipe_list"),
    path("recipes/saved/", recipe_list, name="recipe_saved_list"),
    path("recipes/spoonacular/<int:spoonacular_id>/", recipe_spoonacular_detail, name="recipe_spoonacular_detail"),
    path("recipes/spoonacular/<int:spoonacular_id>/save/", recipe_save_spoonacular, name="recipe_save_spoonacular"),
    path("recipes/new/", recipe_create, name="recipe_create"),
    path("recipes/<int:pk>/", recipe_detail, name="recipe_detail"),
    path("recipes/<int:pk>/edit/", recipe_update, name="recipe_update"),
    path("recipes/<int:pk>/delete/", recipe_delete, name="recipe_delete"),
    path('register/', register_account, name='register_account'),
    path('login/', login_account, name='login_account'),
    path("profile/", show_profile_page, name="show_profile_page"),
    path("logout/", logout_account, name="logout_account"),
    path("profile/delete/", delete_account, name="delete_account"),
    path("profile/details/", show_profile_details, name="show_profile_details"),
    path("profile/edit/", edit_profile_details, name="edit_profile_details"),
    path("profile/change-password/", change_password, name="change_password"),
    path("reactivate/", reactivate_account, name="reactivate_account"),
    path("profile/deactivate/", deactivate_account, name="deactivate_account"),
]

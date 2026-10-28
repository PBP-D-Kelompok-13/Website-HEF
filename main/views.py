from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ProfileDetailsForm,
    CustomPasswordChangeForm,
    ReactivationForm,
    IngredientForm
)
from .models import Ingredient
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from functools import wraps
from django.contrib import messages
from datetime import date, timedelta
import random

# Custom wrapper that only allows HTMX requests
def htmx_only(redirect_to="main:show_landing_page"):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.headers.get("HX-Request") != "true":
                return redirect(redirect_to)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator

''' =============================== 
    Functions for Main Landing Page
    =============================== '''
def show_landing_page(request):
    return render(request, "pages/landing_page.html")

''' =============================== 
    Functions for Authentication
    =============================== '''
def register_account(request):
    if request.user.is_authenticated:
        return redirect('main:show_landing_page')

    form = CustomUserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Account successfully registered. Please log in.")
        return redirect('main:login_account')

    return render(request, 'pages/register.html', {'form': form})

def login_account(request):
    if request.user.is_authenticated:
        return redirect('main:show_landing_page')

    form = CustomAuthenticationForm(
        request,
        data=request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Login successful.")
        return redirect('main:show_landing_page')

    return render(request, 'pages/login.html', {'form': form})

def reactivate_account(request):
    if request.user.is_authenticated:
        return redirect("main:show_landing_page")

    form = ReactivationForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        user = form.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Your account has been reactivated. Please log in.")
        return redirect("main:login_account")

    return render(request, "pages/reactivate_account.html", {"form": form})

@require_POST
def logout_account(request):
    logout(request)
    messages.success(request, "Logout successful.")
    return redirect("main:show_landing_page")

''' =============================== 
    Functions for User Profile Page
    =============================== '''

PROFILE_AVATARS = [
    "img/avatar-1.png",
    "img/avatar-2.png",
    "img/avatar-3.png",
]

@login_required
def show_profile_page(request):
    avatar = random.choice(PROFILE_AVATARS)
    return render(request, "pages/profile_page.html", {"avatar": avatar})

@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Account successfully deleted.")
    return redirect("main:show_landing_page")

@login_required
@htmx_only('main:show_profile_page')
def show_profile_details(request):
    return render(request, "partials/profile_details.html")


@login_required
@htmx_only('main:show_profile_page')
def edit_profile_details(request):
    if request.method == "POST":
        form = ProfileDetailsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account information successfully updated.")
            return render(
                request,
                "partials/profile_details.html",
                {"updated": True, "toast": True},
            )
    else:
        form = ProfileDetailsForm(instance=request.user)
    return render(request, "partials/profile_details_edit.html", {"form": form})

@login_required
@htmx_only("main:show_profile_page")
def change_password(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password successfully changed.")
            return render(
                request, "partials/profile_details.html", {"toast": True}
            )
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(
        request,
        "partials/profile_change_password.html",
        {"form": form},
    )

@login_required
@require_POST
def deactivate_account(request):
    user = request.user
    user.is_active = False
    user.save(update_fields=["is_active"])

    logout(request)
    messages.success(request, "Your account has been deactivated.")

    return redirect("main:show_landing_page")

''' =============================== 
    Functions for Food Inventory
    =============================== '''
@login_required(login_url='main:login_account')
def show_inventory(request):
    ingredients = Ingredient.objects.filter(user=request.user)
    
    search_query = request.GET.get('q', '')
    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)
        
    category_filter = request.GET.get('category', '')
    if category_filter and category_filter != 'All':
        ingredients = ingredients.filter(category=category_filter)

    # Calculate ingredients about to expire (<= 3 days from today)
    today = date.today()
    warning_threshold = today + timedelta(days=3)
    expiring_count = sum(
        1 for item in ingredients 
        if item.expiration_date and item.expiration_date <= warning_threshold
    )

    form = IngredientForm()
    context = {
        'ingredients': ingredients,
        'form': form,
        'search_query': search_query,
        'current_category': category_filter or 'All',
        'expiring_count': expiring_count,
    }
    return render(request, 'pages/inventory.html', context)

@login_required(login_url='main:login_account')
def add_ingredient(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST, request.FILES)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            ingredient.save()
            messages.success(request, "Ingredient successfully added.")
            return redirect('main:show_inventory')
        else:
            messages.error(request, "Failed to add ingredient.")
    else:
        form = IngredientForm()
    return redirect('main:show_inventory')

@login_required(login_url='main:login_account')
def edit_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IngredientForm(request.POST, request.FILES, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingredient successfully editted.")
            return redirect('main:show_inventory')
        else:
            messages.error(request, "Failed to edit ingredient.")
    return redirect('main:show_inventory')

@login_required(login_url='main:login_account')
def delete_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    ingredient.delete()
    return redirect('main:show_inventory')

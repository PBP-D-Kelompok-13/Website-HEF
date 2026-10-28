from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ProfileDetailsForm,
    CustomPasswordChangeForm,
    ReactivationForm,
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from functools import wraps
import random

import requests

from .models import SavedRecipe
from .services.recipe_analyzer import (
    analyze_with_spoonacular, get_spoonacular_recipe, search_spoonacular_recipes,
)

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

# Recipe Analyzer views keep saved data scoped to the signed-in owner.

RECIPE_PAGE_SIZE = 6
ALLOWED_DIETS = {"vegetarian", "vegan", "gluten free"}

def _spoonacular_error(request):
    messages.error(request, "Spoonacular is unavailable right now. Please try again shortly.")


def _nutrients(nutrition):
    if not isinstance(nutrition, dict):
        return []
    values = nutrition.get("nutrients", [])
    if not values and isinstance(nutrition.get("nutrition"), dict):
        values = nutrition["nutrition"].get("nutrients", [])
    return values


def _display_analysis(nutrition):
    nutrients = _nutrients(nutrition)
    wanted = {"Protein", "Carbohydrates", "Fat", "Fiber", "Sugar", "Sodium", "Calories"}
    values = {item.get("name", "").lower(): item for item in nutrients if item.get("name", "").lower() in {name.lower() for name in wanted}}
    calories = values.get("calories", {}).get("amount", 0) or 0
    macros = []
    for name in ("Carbohydrates", "Protein", "Fat"):
        item = values.get(name.lower(), {})
        amount = float(item.get("amount", 0) or 0)
        macros.append({"name": name, "amount": amount, "unit": item.get("unit", "g")})
    macro_energy = [max(item["amount"] * 4, 0) for item in macros]
    total_energy = sum(macro_energy) or 1
    for index, macro in enumerate(macros):
        macro["percentage"] = round(macro_energy[index] * 100 / total_energy)
    nutrition_tiles = [values[name.lower()] for name in ("Protein", "Carbohydrates", "Fat", "Fiber", "Sugar", "Sodium") if name.lower() in values]
    return {"calories": round(float(calories)), "macros": macros, "nutrition_tiles": nutrition_tiles}


@login_required
def recipe_discover(request):
    query = request.GET.get("query", "").strip()[:120]
    diet = request.GET.get("diet", "").strip().lower()
    if diet not in ALLOWED_DIETS:
        diet = ""
    try:
        max_ready_time = int(request.GET.get("maxReadyTime", "") or 0) or None
    except ValueError:
        max_ready_time = None
    if max_ready_time and not 1 <= max_ready_time <= 1440:
        max_ready_time = None
    try:
        offset = max(int(request.GET.get("offset", 0)), 0)
    except ValueError:
        offset = 0
    results = {"results": [], "totalResults": 0, "offset": offset}
    api_error = False
    try:
        results = search_spoonacular_recipes(
            query=query, diet=diet, max_ready_time=max_ready_time, offset=offset
        )
    except (ImproperlyConfigured, requests.RequestException, ValueError):
        api_error = True
        _spoonacular_error(request)
    saved_map = dict(SavedRecipe.objects.filter(
        user=request.user, source=SavedRecipe.Source.SPOONACULAR,
        spoonacular_id__in=[item.get("id") for item in results.get("results", [])],
    ).values_list("spoonacular_id", "pk"))
    search_cards = []
    for item in results.get("results", []):
        search_cards.append({
            **item,
            "analysis": _display_analysis(item.get("nutrition", {})),
            "category": (item.get("cuisines") or item.get("dishTypes") or ["Recipe"])[0].title(),
            "diets": item.get("diets", []),
            "saved_pk": saved_map.get(item.get("id")),
        })
    context = {
        "results": results.get("results", []), "search_cards": search_cards,
        "total_results": results.get("totalResults", 0), "saved_ids": set(saved_map),
        "query": query, "diet": diet, "max_ready_time": max_ready_time or "",
        "offset": offset, "next_offset": offset + RECIPE_PAGE_SIZE,
        "more_available": results.get("totalResults", 0) > offset + RECIPE_PAGE_SIZE,
        "api_error": api_error,
    }
    if request.headers.get("HX-Request") == "true":
        template = "pages/recipes/_discover_more.html" if offset else "pages/recipes/_discover_results.html"
    else:
        template = "pages/recipes/discover.html"
    return render(request, template, context)

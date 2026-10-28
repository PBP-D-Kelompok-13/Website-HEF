from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from .forms import (
    RecipeForm,
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
from .recipe_forms import RecipeAuthorForm, RecipeIngredientFormSet
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


def _owned_recipe(request, pk):
    return get_object_or_404(SavedRecipe, pk=pk, user=request.user)


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


def _ingredient_formset(request, instance=None):
    prefix = "ingredient"
    legacy = request.method == "POST" and f"{prefix}-TOTAL_FORMS" not in request.POST
    data = request.POST
    if legacy:
        lines = [line.strip() for line in request.POST.get("ingredients", "").splitlines() if line.strip()]
        if not lines and instance:
            lines = [line.strip() for line in instance.ingredients.splitlines() if line.strip()]
        if lines:
            data = request.POST.copy()
            data[f"{prefix}-TOTAL_FORMS"] = str(len(lines))
            data[f"{prefix}-INITIAL_FORMS"] = "0"
            data[f"{prefix}-MIN_NUM_FORMS"] = "1"
            data[f"{prefix}-MAX_NUM_FORMS"] = "30"
            for index, line in enumerate(lines):
                data[f"{prefix}-{index}-name"] = line
                data[f"{prefix}-{index}-amount_g"] = ""
    initial = instance.ingredient_items if instance and instance.ingredient_items else None
    if request.method == "GET" and initial is None and instance:
        initial = [{"name": line, "amount_g": ""} for line in instance.ingredients.splitlines() if line]
    formset = RecipeIngredientFormSet(
        data if request.method == "POST" else None,
        initial=initial, prefix=prefix,
        form_kwargs={"require_weight": not legacy},
    )
    return formset


def _ingredient_rows(formset):
    return [
        {"name": form.cleaned_data["name"], "amount_g": format(form.cleaned_data["amount_g"], "f") if form.cleaned_data.get("amount_g") else ""}
        for form in formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE") and form.cleaned_data.get("name")
    ]


def _ingredient_text(items):
    return "\n".join(
        f"{item['name']} — {item['amount_g']} g" if item.get("amount_g") else item["name"]
        for item in items
    )


def _analyze_own_recipe(recipe, items):
    api_ingredients = [f"{item['amount_g']} g {item['name']}" for item in items]
    return analyze_with_spoonacular(
        title=recipe.title, ingredients=api_ingredients,
        instructions=recipe.instructions, servings=recipe.servings,
    )


@login_required
def recipe_create(request):
    form = RecipeAuthorForm(request.POST or None, request.FILES or None)
    ingredient_formset = _ingredient_formset(request)
    if request.method == "POST" and form.is_valid() and ingredient_formset.is_valid():
        recipe = form.save(commit=False)
        recipe.user = request.user
        recipe.source = SavedRecipe.Source.OWN
        recipe.ingredient_items = _ingredient_rows(ingredient_formset)
        recipe.ingredients = _ingredient_text(recipe.ingredient_items)
        action = request.POST.get("action", "analyze")
        if action == "draft":
            recipe.is_draft = True
            recipe.save()
            messages.success(request, "Draft saved under My recipes.")
            return redirect("main:recipe_detail", pk=recipe.pk)
        try:
            recipe.nutrition = analyze_with_spoonacular(
                title=recipe.title,
                ingredients=[f"{item['amount_g']} g {item['name']}" if item.get("amount_g") else item["name"] for item in recipe.ingredient_items],
                instructions=recipe.instructions,
                servings=recipe.servings,
            )
        except (ImproperlyConfigured, requests.RequestException, ValueError):
            _spoonacular_error(request)
            return render(request, "pages/recipes/form.html", {"form": form, "ingredient_formset": ingredient_formset, "editing": False}, status=502)
        recipe.health_score = recipe.nutrition.get("healthScore")
        recipe.diets = recipe.nutrition.get("diets", [])
        recipe.is_draft = False
        recipe.save()
        messages.success(request, "Recipe analyzed and saved.")
        return redirect("main:recipe_detail", pk=recipe.pk)
    return render(request, "pages/recipes/form.html", {"form": form, "ingredient_formset": ingredient_formset, "editing": False})


@login_required
def recipe_update(request, pk):
    recipe = _owned_recipe(request, pk)
    form = RecipeAuthorForm(request.POST or None, request.FILES or None, instance=recipe)
    ingredient_formset = _ingredient_formset(request, recipe)
    if request.method == "POST" and form.is_valid() and ingredient_formset.is_valid():
        updated = form.save(commit=False)
        updated.ingredient_items = _ingredient_rows(ingredient_formset)
        updated.ingredients = _ingredient_text(updated.ingredient_items)
        if request.POST.get("action", "analyze") == "draft":
            updated.is_draft = True
            updated.save()
            messages.success(request, "Draft updated.")
            return redirect("main:recipe_detail", pk=updated.pk)
        try:
            updated.nutrition = analyze_with_spoonacular(
                title=updated.title,
                ingredients=[f"{item['amount_g']} g {item['name']}" if item.get("amount_g") else item["name"] for item in updated.ingredient_items],
                instructions=updated.instructions, servings=updated.servings,
            )
        except (ImproperlyConfigured, requests.RequestException, ValueError):
            _spoonacular_error(request)
            return render(request, "pages/recipes/form.html", {"form": form, "ingredient_formset": ingredient_formset, "recipe": recipe, "editing": True}, status=502)
        updated.health_score = updated.nutrition.get("healthScore")
        updated.diets = updated.nutrition.get("diets", [])
        updated.is_draft = False
        updated.save()
        messages.success(request, "Recipe updated and analyzed.")
        return redirect("main:recipe_detail", pk=updated.pk)
    return render(request, "pages/recipes/form.html", {"form": form, "ingredient_formset": ingredient_formset, "recipe": recipe, "editing": True})


@login_required
@require_POST
def recipe_delete(request, pk):
    recipe = _owned_recipe(request, pk)
    recipe.delete()
    messages.success(request, "Recipe removed from My recipes.")
    if request.headers.get("HX-Request") == "true":
        return HttpResponse(headers={"HX-Redirect": reverse("main:recipe_saved_list")})
    return redirect("main:recipe_saved_list")

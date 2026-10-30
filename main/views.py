from django.views.decorators.http import require_GET
from .comparison_views import build_comparison_context
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.vary import vary_on_headers
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core import serializers
from datetime import date, timedelta
from functools import wraps
import random
import requests

from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ProfileDetailsForm,
    CustomPasswordChangeForm,
    ReactivationForm,
    IngredientForm,
    ProductForm,
)
from .models import Bookmark, Ingredient, Product, SavedRecipe
from .services import fetch_and_save_product
from .recipe_forms import RecipeAuthorForm, RecipeIngredientFormSet
from .services.recipe_analyzer import (
    RECIPE_PAGE_SIZE,
    analyze_with_spoonacular,
    get_spoonacular_recipe,
    search_spoonacular_recipes,
    search_spoonacular_ingredients,
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


""" ===============================
    Functions for Main Landing Page
    =============================== """


def show_landing_page(request):
    return render(request, "pages/landing_page.html")


""" ===============================
    Functions for Authentication
    =============================== """


def register_account(request):
    if request.user.is_authenticated:
        return redirect("main:show_landing_page")

    form = CustomUserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account successfully registered. Please log in.")
        return redirect("main:login_account")

    return render(request, "pages/register.html", {"form": form})


def login_account(request):
    if request.user.is_authenticated:
        return redirect("main:show_landing_page")

    form = CustomAuthenticationForm(
        request,
        data=request.POST if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Login successful.")
        return redirect("main:show_landing_page")

    return render(request, "pages/login.html", {"form": form})


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


""" =============================== 
    Functions for User Profile Page
    =============================== """

PROFILE_AVATARS = [
    "img/avatar-1.png",
    "img/avatar-2.png",
    "img/avatar-3.png",
]


@login_required
def show_profile_page(request):
    avatar = random.choice(PROFILE_AVATARS)
    saved_recipe = (
        SavedRecipe.objects.filter(user=request.user).order_by("-created_at").first()
    )
    ingredients = Ingredient.objects.filter(user=request.user).order_by("created_at")[:3]
    context = {
        "avatar": avatar,
        "ingredients": ingredients,
        "saved_recipe": saved_recipe,
    }

    return render(request, "pages/profile_page.html", context)


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Account successfully deleted.")
    return redirect("main:show_landing_page")


@login_required
@htmx_only("main:show_profile_page")
def show_profile_details(request):
    return render(request, "partials/profile_details.html")


@login_required
@htmx_only("main:show_profile_page")
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
            return render(request, "partials/profile_details.html", {"toast": True})
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

@login_required
@require_GET
@vary_on_headers("HX-Request")
def show_compare(request):
    context = build_comparison_context(request)
    requested = request.GET.get("run") == "1"

    context["show_results"] = requested and context["can_compare"]

    if requested and not context["can_compare"]:
        context["comparison_error"] = (
            "Choose 2–3 different, available products before comparing."
        )

    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        template = "partials/compare_workspace.html"
    else:
        template = "pages/compare.html"

    # HTMX menampilkan pesan validasi sebagai HTML.
    # Request halaman biasa menerima status 400 jika pilihan tidak valid.
    status = 200
    if requested and not context["can_compare"] and not is_htmx:
        status = 400

    return render(request, template, context, status=status)

""" =============================== 
    Recipe
    =============================== """
# Recipe Analyzer views keep saved data scoped to the signed-in owner.

ALLOWED_DIETS = {"vegetarian", "vegan", "gluten free"}


@login_required
def recipe_ingredient_suggestions(request):
    query = (
        request.GET.get("q")
        or next(
            (value for key, value in request.GET.items() if key.endswith("-name")), ""
        )
    ).strip()[:80]
    suggestions = []
    if len(query) >= 2:
        try:
            suggestions = search_spoonacular_ingredients(query)
        except (ImproperlyConfigured, requests.RequestException, ValueError):
            suggestions = []
    normalized_suggestions = []
    if isinstance(suggestions, list):
        for item in suggestions[:8]:
            name = item.get("name") if isinstance(item, dict) else None
            if isinstance(name, str) and name.strip():
                normalized_suggestions.append({"name": name.strip()})
    suggestions = normalized_suggestions
    return render(
        request,
        "pages/recipes/_ingredient_suggestions.html",
        {"suggestions": suggestions},
    )


def _owned_recipe(request, pk):
    return get_object_or_404(SavedRecipe, pk=pk, user=request.user)


def _spoonacular_error(request):
    messages.error(
        request, "Spoonacular is unavailable right now. Please try again shortly."
    )


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
    wanted_names = {name.lower() for name in wanted}
    values = {
        item.get("name", "").lower(): item
        for item in nutrients
        if item.get("name", "").lower() in wanted_names
    }
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
    nutrition_tiles = [
        values[name.lower()]
        for name in ("Protein", "Carbohydrates", "Fat", "Fiber", "Sugar", "Sodium")
        if name.lower() in values
    ]
    return {
        "calories": round(float(calories)),
        "macros": macros,
        "nutrition_tiles": nutrition_tiles,
    }


def _instruction_steps(value):
    if isinstance(value, list):
        steps = []
        for group in value:
            for item in group.get("steps", []):
                steps.append(item.get("step", ""))
        return [step for step in steps if step]
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _detail_context(recipe, *, spoonacular=False):
    if spoonacular:
        nutrition = recipe.get("nutrition", {})
        ingredients = recipe.get("extendedIngredients", [])
        return {
            "recipe": recipe,
            "recipe_description": strip_tags(recipe.get("summary", "")),
            "nutrition_view": _display_analysis(nutrition),
            "ingredients_view": ingredients,
            "steps": _instruction_steps(recipe.get("analyzedInstructions", []))
            or _instruction_steps(recipe.get("instructions", "")),
            "is_spoonacular": True,
            "source_url": recipe.get("sourceUrl", ""),
            "ready_time": recipe.get("readyInMinutes"),
            "health_score": recipe.get("healthScore"),
            "image_url": recipe.get("image", ""),
        }
    nutrition = recipe.nutrition or {}
    if recipe.source == SavedRecipe.Source.SPOONACULAR:
        ingredients = recipe.ingredient_items
        steps = _instruction_steps(
            nutrition.get("analyzedInstructions", [])
        ) or _instruction_steps(recipe.instructions)
        nutrition = nutrition.get("nutrition", nutrition)
    else:
        ingredients = recipe.ingredient_items or [
            {"name": line, "amount_g": ""}
            for line in recipe.ingredients.splitlines()
            if line
        ]
        steps = _instruction_steps(recipe.instructions)
    return {
        "recipe": recipe,
        "recipe_description": recipe.description,
        "nutrition_view": _display_analysis(nutrition),
        "ingredients_view": ingredients,
        "steps": steps,
        "is_spoonacular": recipe.source == SavedRecipe.Source.SPOONACULAR,
        "saved_recipe": (
            recipe if recipe.source == SavedRecipe.Source.SPOONACULAR else None
        ),
        "ready_time": recipe.ready_in_minutes,
        "health_score": recipe.health_score,
        "image_url": recipe.image_url or (recipe.photo.url if recipe.photo else ""),
        "source_url": recipe.source_url,
    }


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
    saved_map = dict(
        SavedRecipe.objects.filter(
            user=request.user,
            source=SavedRecipe.Source.SPOONACULAR,
            spoonacular_id__in=[item.get("id") for item in results.get("results", [])],
        ).values_list("spoonacular_id", "pk")
    )
    search_cards = []
    for item in results.get("results", []):
        search_cards.append(
            {
                **item,
                "analysis": _display_analysis(item.get("nutrition", {})),
                "category": (
                    item.get("cuisines") or item.get("dishTypes") or ["Recipe"]
                )[0].title(),
                "diets": item.get("diets", []),
                "saved_pk": saved_map.get(item.get("id")),
            }
        )
    context = {
        "search_cards": search_cards,
        "total_results": results.get("totalResults", 0),
        "query": query,
        "diet": diet,
        "max_ready_time": max_ready_time or "",
        "next_offset": offset + RECIPE_PAGE_SIZE,
        "more_available": results.get("totalResults", 0) > offset + RECIPE_PAGE_SIZE,
        "api_error": api_error,
    }
    if request.headers.get("HX-Request") == "true":
        template = (
            "pages/recipes/_discover_more.html"
            if offset
            else "pages/recipes/_discover_results.html"
        )
    else:
        template = "pages/recipes/discover.html"
    return render(request, template, context)


@login_required
def recipe_list(request):
    saved = SavedRecipe.objects.filter(user=request.user)
    query = request.GET.get("query", "").strip()[:120]
    if query:
        saved = saved.filter(title__icontains=query)
    sort = request.GET.get("sort", "newest")
    sort_fields = {"newest": "-created_at", "oldest": "created_at", "title": "title"}
    saved = saved.order_by(sort_fields.get(sort, "-created_at"))
    spoonacular_recipes = saved.filter(source=SavedRecipe.Source.SPOONACULAR)
    own_recipes = saved.filter(source=SavedRecipe.Source.OWN)
    return render(
        request,
        "pages/recipes/saved.html",
        {
            "spoonacular_recipes": [
                {"recipe": item, "analysis": _display_analysis(item.nutrition)}
                for item in spoonacular_recipes
            ],
            "own_recipes": [
                {"recipe": item, "analysis": _display_analysis(item.nutrition)}
                for item in own_recipes
            ],
            "query": query,
            "sort": sort if sort in sort_fields else "newest",
        },
    )


def _ingredient_formset(request, instance=None):
    prefix = "ingredient"
    legacy = request.method == "POST" and f"{prefix}-TOTAL_FORMS" not in request.POST
    data = request.POST
    if legacy:
        lines = [
            line.strip()
            for line in request.POST.get("ingredients", "").splitlines()
            if line.strip()
        ]
        if not lines and instance:
            lines = [
                line.strip()
                for line in instance.ingredients.splitlines()
                if line.strip()
            ]
        if lines:
            data = request.POST.copy()
            data[f"{prefix}-TOTAL_FORMS"] = str(len(lines))
            data[f"{prefix}-INITIAL_FORMS"] = "0"
            data[f"{prefix}-MIN_NUM_FORMS"] = "1"
            data[f"{prefix}-MAX_NUM_FORMS"] = "30"
            for index, line in enumerate(lines):
                data[f"{prefix}-{index}-name"] = line
                data[f"{prefix}-{index}-amount_g"] = ""
    initial = (
        instance.ingredient_items if instance and instance.ingredient_items else None
    )
    if request.method == "GET" and initial is None and instance:
        initial = [
            {"name": line, "amount_g": ""}
            for line in instance.ingredients.splitlines()
            if line
        ]
    formset = RecipeIngredientFormSet(
        data if request.method == "POST" else None,
        initial=initial,
        prefix=prefix,
        form_kwargs={"require_weight": not legacy},
    )
    return formset


def _ingredient_rows(formset):
    return [
        {
            "name": form.cleaned_data["name"],
            "amount_g": (
                format(form.cleaned_data["amount_g"], "f")
                if form.cleaned_data.get("amount_g")
                else ""
            ),
        }
        for form in formset.forms
        if form.cleaned_data
        and not form.cleaned_data.get("DELETE")
        and form.cleaned_data.get("name")
    ]


def _ingredient_text(items):
    return "\n".join(
        (
            f"{item['name']} — {item['amount_g']} g"
            if item.get("amount_g")
            else item["name"]
        )
        for item in items
    )


def _analyze_own_recipe(recipe):
    ingredients = [
        f"{item['amount_g']} g {item['name']}" if item.get("amount_g") else item["name"]
        for item in recipe.ingredient_items
    ]
    return analyze_with_spoonacular(
        title=recipe.title,
        ingredients=ingredients,
        instructions=recipe.instructions,
        servings=recipe.servings,
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
            recipe.nutrition = _analyze_own_recipe(recipe)
        except (ImproperlyConfigured, requests.RequestException, ValueError):
            _spoonacular_error(request)
            return render(
                request,
                "pages/recipes/form.html",
                {
                    "form": form,
                    "ingredient_formset": ingredient_formset,
                    "editing": False,
                },
                status=502,
            )
        recipe.health_score = recipe.nutrition.get("healthScore")
        recipe.diets = recipe.nutrition.get("diets", [])
        recipe.is_draft = False
        recipe.save()
        messages.success(request, "Recipe analyzed and saved.")
        return redirect("main:recipe_detail", pk=recipe.pk)
    return render(
        request,
        "pages/recipes/form.html",
        {"form": form, "ingredient_formset": ingredient_formset, "editing": False},
    )


@login_required
def recipe_detail(request, pk):
    recipe = _owned_recipe(request, pk)
    return render(request, "pages/recipes/detail.html", _detail_context(recipe))


@login_required
def recipe_update(request, pk):
    recipe = _owned_recipe(request, pk)
    form = RecipeAuthorForm(
        request.POST or None, request.FILES or None, instance=recipe
    )
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
            updated.nutrition = _analyze_own_recipe(updated)
        except (ImproperlyConfigured, requests.RequestException, ValueError):
            _spoonacular_error(request)
            return render(
                request,
                "pages/recipes/form.html",
                {
                    "form": form,
                    "ingredient_formset": ingredient_formset,
                    "recipe": recipe,
                    "editing": True,
                },
                status=502,
            )
        updated.health_score = updated.nutrition.get("healthScore")
        updated.diets = updated.nutrition.get("diets", [])
        updated.is_draft = False
        updated.save()
        messages.success(request, "Recipe updated and analyzed.")
        return redirect("main:recipe_detail", pk=updated.pk)
    return render(
        request,
        "pages/recipes/form.html",
        {
            "form": form,
            "ingredient_formset": ingredient_formset,
            "recipe": recipe,
            "editing": True,
        },
    )


@login_required
def recipe_spoonacular_detail(request, spoonacular_id):
    try:
        data = get_spoonacular_recipe(spoonacular_id)
    except (ImproperlyConfigured, requests.RequestException, ValueError):
        _spoonacular_error(request)
        return redirect("main:recipe_discover")
    saved = SavedRecipe.objects.filter(
        user=request.user,
        spoonacular_id=spoonacular_id,
        source=SavedRecipe.Source.SPOONACULAR,
    ).first()
    context = _detail_context(data, spoonacular=True)
    context.update({"saved_recipe": saved, "back_query": request.GET.get("query", "")})
    return render(request, "pages/recipes/detail.html", context)


@login_required
@require_POST
def recipe_save_spoonacular(request, spoonacular_id):
    try:
        data = get_spoonacular_recipe(spoonacular_id)
    except (ImproperlyConfigured, requests.RequestException, ValueError):
        _spoonacular_error(request)
        return redirect("main:recipe_discover")
    items = [
        {
            "name": item.get("name", ""),
            "amount": item.get("amount", ""),
            "unit": item.get("unit", ""),
            "original": item.get("original", ""),
        }
        for item in data.get("extendedIngredients", [])
    ]
    saved, created = SavedRecipe.objects.get_or_create(
        user=request.user,
        source=SavedRecipe.Source.SPOONACULAR,
        spoonacular_id=spoonacular_id,
        defaults={
            "title": data.get("title", "Saved recipe")[:120],
            "description": strip_tags(data.get("summary", ""))[:4000],
            "ingredients": "\n".join(item.get("original", "") for item in items),
            "ingredient_items": items,
            "instructions": data.get("instructions", "") or "",
            "servings": data.get("servings") or 1,
            "ready_in_minutes": data.get("readyInMinutes"),
            "health_score": data.get("healthScore"),
            "diets": data.get("diets", []),
            "nutrition": data.get("nutrition", {}),
            "image_url": data.get("image", ""),
            "source_url": data.get("sourceUrl", ""),
        },
    )
    messages.success(
        request, "Recipe saved." if created else "Recipe is already in My recipes."
    )
    if request.headers.get("HX-Request") == "true":
        return HttpResponse(headers={"HX-Redirect": reverse("main:recipe_saved_list")})
    return redirect("main:recipe_saved_list")


""" ===============================
    Functions for Food Inventory
    =============================== """


@login_required(login_url="main:login_account")
def show_inventory(request):
    ingredients = Ingredient.objects.filter(user=request.user)

    search_query = request.GET.get("q", "")
    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    category_filter = request.GET.get("category", "")
    if category_filter and category_filter != "All":
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
        "ingredients": ingredients,
        "form": form,
        "search_query": search_query,
        "current_category": category_filter or "All",
        "expiring_count": expiring_count,
    }
    return render(request, "pages/inventory.html", context)


@login_required(login_url="main:login_account")
def add_ingredient(request):
    if request.method == "POST":
        form = IngredientForm(request.POST, request.FILES)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            ingredient.save()
            messages.success(request, "Ingredient successfully added.")
            return redirect("main:show_inventory")
        else:
            messages.error(request, "Failed to add ingredient.")
    else:
        form = IngredientForm()
    return redirect("main:show_inventory")


@login_required(login_url="main:login_account")
def edit_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    if request.method == "POST":
        form = IngredientForm(request.POST, request.FILES, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingredient successfully edited.")
            return redirect("main:show_inventory")
        else:
            messages.error(request, "Failed to edit ingredient.")
    return redirect("main:show_inventory")


@login_required(login_url="main:login_account")
def delete_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    ingredient.delete()
    return redirect("main:show_inventory")


def get_ingredients_json(request):
    name_query = request.GET.get("name", "").strip()
    ingredients = (
        Ingredient.objects.filter(user=request.user)
        if request.user.is_authenticated
        else Ingredient.objects.none()
    )

    if name_query:
        ingredients = ingredients.filter(name__icontains=name_query)

    ingredients_json = serializers.serialize("json", ingredients)
    return HttpResponse(ingredients_json, content_type="application/json")


""" ===============================
    Functions for Discover & Products
    =============================== """

PAGE_SIZE = 6


def _is_htmx(request):
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def _filtered_products(request):
    params = request.GET
    query = params.get("q", "").strip()
    category = params.get("category", "all").strip()
    eco = params.get("eco", "").strip().lower()
    nutri = params.get("nutri", "").strip().lower()
    saved_only = params.get("saved") == "1" and request.user.is_authenticated
    sort = params.get("sort", "eco").strip()
    if sort not in {"eco", "name", "newest"}:
        sort = "eco"

    qs = (
        Product.objects.search(query)
        .filter_by(
            category=category,
            eco=eco,
            nutri=nutri,
            saved_by=request.user if saved_only else None,
            sort=sort,
        )
        .with_saved_flag(request.user)
    )
    filters = {
        "q": query,
        "category": category or "all",
        "eco": eco,
        "nutri": nutri,
        "saved": "1" if saved_only else "",
        "sort": sort,
    }
    return qs, filters


@vary_on_headers("HX-Request")
def discover(request):
    qs, filters = _filtered_products(request)
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    query = filters["q"]

    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
        "shown_count": page_obj.end_index() if paginator.count else 0,
        "filters": filters,
        "filter_querystring": params.urlencode(),
        "categories": [c[0] for c in Product.CATEGORIES],
        "grades": Product.GRADES,
        "can_lookup_barcode": query.isdigit() and 8 <= len(query) <= 14,
    }

    if _is_htmx(request):
        if request.GET.get("page"):
            return render(request, "partials/discover_more.html", context)
        return render(request, "partials/discover_results.html", context)
    return render(request, "pages/discover.html", context)


def _can_manage(user, product):
    return user.is_authenticated and (user.is_staff or product.created_by_id == user.id)


def product_detail(request, barcode):
    product = get_object_or_404(
        Product.objects.with_saved_flag(request.user), barcode=barcode
    )
    nutrients = [
        ("Sugars", product.sugars_100g, "g", product.sugars_level),
        ("Salt", product.salt_100g, "g", product.salt_level),
        ("Fat", product.fat_100g, "g", product.fat_level),
    ]
    return render(
        request,
        "pages/product_detail.html",
        {
            "product": product,
            "grades": Product.GRADES,
            "nutrients": nutrients,
            "can_manage": _can_manage(request.user, product),
        },
    )


@login_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.created_by = request.user
        product.save()
        messages.success(request, "Product successfully added.")
        return redirect("main:product_detail", barcode=product.barcode)
    return render(
        request,
        "pages/product_form.html",
        {"form": form, "is_edit": False},
    )


@login_required
def product_edit(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    if not _can_manage(request.user, product):
        return HttpResponseForbidden("You cannot edit this product.")
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product successfully updated.")
        return redirect("main:product_detail", barcode=product.barcode)
    return render(
        request,
        "pages/product_form.html",
        {"form": form, "product": product, "is_edit": True},
    )


@login_required
@require_POST
def recipe_delete(request, pk):
    recipe = _owned_recipe(request, pk)
    recipe.delete()
    messages.success(request, "Recipe removed from My recipes.")
    if request.headers.get("HX-Request") == "true":
        return HttpResponse(headers={"HX-Redirect": reverse("main:recipe_saved_list")})
    return redirect("main:recipe_saved_list")


@login_required
@require_POST
def product_delete(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    if not _can_manage(request.user, product):
        return HttpResponseForbidden("You cannot delete this product.")
    product.delete()
    messages.success(request, "Product successfully deleted.")
    return redirect("main:discover")


def lookup_product(request, barcode):
    barcode = (barcode or "").strip()
    if not barcode.isdigit() or not (8 <= len(barcode) <= 14):
        messages.error(request, "Please enter a valid barcode (8-14 digits).")
        return redirect("main:discover")

    product = Product.objects.filter(barcode=barcode).first()
    if not product:
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to import new products.")
            return redirect("main:login_account")
        product = fetch_and_save_product(barcode, user=request.user)
        if product:
            messages.success(request, f"{product.name} added to Discover.")
    if not product:
        messages.error(request, f"Barcode {barcode} was not found on Open Food Facts.")
        return redirect("main:discover")
    return redirect("main:product_detail", barcode=product.barcode)


def htmx_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to save products.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("main:login_account")
            return response
        return view(request, *args, **kwargs)

    return wrapper


@require_POST
@htmx_only("main:discover")
@htmx_login_required
def toggle_bookmark(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user, product=product
    )
    if created:
        messages.success(request, f"Saved {product.name}.")
    else:
        bookmark.delete()
        messages.info(request, f"Removed {product.name} from saved.")
    return render(
        request,
        "partials/bookmark_toggle.html",
        {"product": product, "saved": created},
    )


def products_json(request):
    qs, _ = _filtered_products(request)
    return JsonResponse(
        {"count": qs.count(), "results": [p.to_dict() for p in qs[:50]]}
    )


def product_json(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    return JsonResponse(product.to_dict())
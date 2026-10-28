from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ProfileDetailsForm,
    CustomPasswordChangeForm,
    ReactivationForm,
)
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from functools import wraps
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


from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.vary import vary_on_headers
from .models import Bookmark, Product
from .services import fetch_and_save_product


''' =============================== 
    Functions for Discover & Products
    =============================== '''

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


def product_create(request):
    return HttpResponse("ok")


def product_edit(request, barcode):
    return HttpResponse("ok")


def product_delete(request, barcode):
    return HttpResponse("ok")


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


def toggle_bookmark(request, barcode):
    return HttpResponse("ok")


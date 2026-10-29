from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .comparison_selection import add_product, remove_product


SESSION_KEY = "comparison_barcodes"


class ProductSourceUnavailable(Exception):
    """Model produk bersama belum tersedia."""


def resolve_product(barcode):
    """Cari produk dari model yang digunakan modul Discover."""
    try:
        product_model = apps.get_model("main", "Product")
    except LookupError as exc:
        raise ProductSourceUnavailable(
            "Sumber produk Discover belum tersedia."
        ) from exc

    return product_model.objects.filter(barcode=barcode).first()

def comparison_add_error(request, errors, status):
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "partials/compare_add_feedback.html",
            {"errors": errors},
        )

    return JsonResponse(
        {"ok": False, "errors": errors},
        status=status,
    )


@login_required
@require_POST
def compare_add(request):
    barcode = request.POST.get("barcode", "").strip()
    selected = request.session.get(SESSION_KEY, [])

    try:
        updated_selection = add_product(selected, barcode)
    except ValidationError as exc:
        return comparison_add_error(request, exc.messages, 400)

    try:
        product = resolve_product(barcode)
    except ProductSourceUnavailable:
        return comparison_add_error(
            request,
            [
                "Sumber produk belum tersedia. "
                "Silakan coba lagi setelah Discover terhubung."
            ],
            503,
        )

    if product is None:
        return comparison_add_error(
            request,
            ["Produk tidak ditemukan."],
            404,
        )

    request.session[SESSION_KEY] = updated_selection

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse()
        response["HX-Redirect"] = reverse("main:show_compare")
        return response

    return JsonResponse(
        {
            "ok": True,
            "barcodes": updated_selection,
            "count": len(updated_selection),
            "can_compare": len(updated_selection) >= 2,
        }
    )
    
@login_required
@require_POST
def compare_remove(request):
    barcode = request.POST.get("barcode", "").strip()

    if not barcode:
        return JsonResponse(
            {
                "ok": False,
                "errors": ["Identitas produk tidak boleh kosong."],
            },
            status=400,
        )

    selected = request.session.get(SESSION_KEY, [])

    try:
        updated_selection = remove_product(selected, barcode)
    except ValidationError as exc:
        return JsonResponse(
            {"ok": False, "errors": exc.messages},
            status=400,
        )

    request.session[SESSION_KEY] = updated_selection
    
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "partials/compare_workspace.html",
            build_comparison_context(request),
        )

    return JsonResponse(
        {
            "ok": True,
            "barcodes": updated_selection,
            "count": len(updated_selection),
            "can_compare": len(updated_selection) >= 2,
        }
    )
    
def display_grade(value):
    """Hanya tampilkan grade A–E; data kosong tetap tidak tersedia."""
    if not isinstance(value, str):
        return ""

    grade = value.strip().lower()
    return grade if grade in {"a", "b", "c", "d", "e"} else ""


def build_comparison_context(request):
    selected = request.session.get(SESSION_KEY, [])
    products = []
    source_unavailable = False

    for barcode in selected:
        try:
            product = resolve_product(barcode)
        except ProductSourceUnavailable:
            product = None
            source_unavailable = True

        if product is None:
            products.append({
                "barcode": barcode,
                "name": "Product unavailable",
                "brand": "",
                "image_url": "",
                "eco_grade": "",
                "nutri_grade": "",
                "available": False,
            })
            continue

        image_url = product.image_url or ""
        if not image_url.startswith(("https://", "http://")):
            image_url = ""

        products.append({
            "barcode": barcode,
            "name": product.name,
            "brand": product.brand,
            "image_url": image_url,
            "eco_grade": display_grade(product.eco_grade),
            "nutri_grade": display_grade(product.nutri_grade),
            "available": True,
        })

    return {
        "products": products,
        "slots": products + [None] * max(0, 3 - len(products)),
        "selected_count": len(products),
        "source_unavailable": source_unavailable,
        "can_compare": (
            2 <= len(products) <= 3
            and len(set(selected)) == len(selected)
            and all(product["available"] for product in products)
        ),
    }
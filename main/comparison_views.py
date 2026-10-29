from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)
from django.core.paginator import Paginator
from .models import Product, SavedComparison
from django.views.decorators.cache import never_cache
from .comparison_forms import SavedComparisonForm

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
        response = render(
            request,
            "partials/compare_add_feedback.html",
            {"errors": errors},
        )

        if request.POST.get("source") == "workspace":
            response["HX-Retarget"] = "#compare-picker-feedback"
            response["HX-Reswap"] = "innerHTML"

        return response

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
        if request.POST.get("source") == "workspace":
            context = build_comparison_context(request)
            context["show_results"] = False

            response = render(
                request,
                "partials/compare_workspace.html",
                context,
            )
            response["HX-Trigger-After-Swap"] = "compareProductAdded"
            return response

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
    return build_comparison_context_for_barcodes(selected)


def build_comparison_context_for_barcodes(selected):
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
        "show_results": False,
        "selected_count": len(products),
        "source_unavailable": source_unavailable,
        "can_compare": (
            2 <= len(products) <= 3
            and len(set(selected)) == len(selected)
            and all(product["available"] for product in products)
        ),
    }

@login_required
@require_GET
def compare_product_picker(request):
    """Tampilkan produk Discover yang belum masuk pilihan Compare."""
    query = request.GET.get("q", "").strip()[:120]
    selected = request.session.get(SESSION_KEY, [])

    queryset = (
        Product.objects.search(query)
        .exclude(barcode__in=selected)
        .order_by("name", "barcode")
    )

    page = Paginator(queryset, 3).get_page(request.GET.get("page"))

    for product in page.object_list:
        image_url = product.image_url or ""
        product.picker_image_url = (
            image_url
            if image_url.startswith(("https://", "http://"))
            else ""
        )

    template = "partials/compare_product_picker.html"

    if request.GET.get("results") == "1":
        template = "partials/compare_picker_results.html"

    return render(
        request,
        template,
        {
            "query": query,
            "page": page,
        },
    )
    
@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def compare_save(request):
    selected = request.session.get(SESSION_KEY, [])
    is_htmx = request.headers.get("HX-Request") == "true"

    form = SavedComparisonForm(
        request.POST if request.method == "POST" else None,
        selected_barcodes=selected,
    )

    if request.method == "POST":
        if form.is_valid():
            comparison = SavedComparison(
                user=request.user,
                title=form.cleaned_data["title"],
                barcodes=list(form.cleaned_data["barcodes"]),
            )

            comparison.full_clean()
            comparison.save()

            if is_htmx:
                response = render(
                    request,
                    "partials/compare_save_success.html",
                    {"comparison": comparison},
                )
                response["HX-Trigger-After-Swap"] = "comparisonSaved"
                return response

            return JsonResponse(
                {
                    "ok": True,
                    "comparison_id": comparison.pk,
                    "title": comparison.title,
                },
                status=201,
            )

        if not is_htmx:
            return JsonResponse(
                {
                    "ok": False,
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )

    selected_count = (
        len(selected)
        if isinstance(selected, (list, tuple))
        else 0
    )

    return render(
        request,
        "partials/compare_save_form.html",
        {
            "form": form,
            "selected_count": selected_count,
        },
    )

@login_required
@require_GET
@never_cache
@vary_on_headers("HX-Request")
def compare_saved_list(request):
    query = request.GET.get("q", "").strip()[:120]
    count_filter = request.GET.get("count", "all")

    if count_filter not in {"2", "3"}:
        count_filter = "all"

    owned = SavedComparison.objects.filter(user=request.user)
    has_saved_comparisons = owned.exists()

    comparisons = owned

    if query:
        comparisons = comparisons.filter(title__icontains=query)

    if count_filter == "2":
        comparisons = comparisons.filter(
            barcodes__1__isnull=False,
            barcodes__2__isnull=True,
        )
    elif count_filter == "3":
        comparisons = comparisons.filter(
            barcodes__2__isnull=False,
            barcodes__3__isnull=True,
        )

    comparisons = comparisons.order_by("-updated_at", "-pk")
    page = Paginator(comparisons, 6).get_page(request.GET.get("page"))

    records = []

    for comparison in page:
        product_context = build_comparison_context_for_barcodes(
            comparison.barcodes
        )

        records.append(
            {
                "comparison": comparison,
                "products": product_context["products"],
                "product_count": len(comparison.barcodes),
            }
        )

    context = {
        "records": records,
        "page": page,
        "query": query,
        "count_filter": count_filter,
        "count_options": (
            ("all", "All"),
            ("2", "2 products"),
            ("3", "3 products"),
        ),
        "has_saved_comparisons": has_saved_comparisons,
    }

    template = "pages/compare_saved.html"

    if request.headers.get("HX-Request") == "true":
        template = "partials/compare_saved_results.html"

    return render(request, template, context)


@login_required
@require_GET
@never_cache
def compare_saved_detail(request, pk):
    comparison = get_object_or_404(
        SavedComparison,
        pk=pk,
        user=request.user,
    )

    context = build_comparison_context_for_barcodes(
        comparison.barcodes
    )
    products = context["products"]

    context.update(
        {
            "comparison": comparison,
            "has_unavailable_products": any(
                not product["available"]
                for product in products
            ),
            "score_rows": [
                {
                    "label": "Eco-Score",
                    "description": "Environmental impact",
                    "grades": [
                        product["eco_grade"]
                        for product in products
                    ],
                },
                {
                    "label": "Nutri-Score",
                    "description": "Nutritional quality",
                    "grades": [
                        product["nutri_grade"]
                        for product in products
                    ],
                },
            ],
        }
    )

    return render(
        request,
        "pages/compare_saved_detail.html",
        context,
    )
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .comparison_selection import add_product


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


@login_required
@require_POST
def compare_add(request):
    barcode = request.POST.get("barcode", "").strip()
    selected = request.session.get(SESSION_KEY, [])

    # Validasi dahulu tanpa mengubah pilihan di session.
    try:
        updated_selection = add_product(selected, barcode)
    except ValidationError as exc:
        return JsonResponse(
            {"ok": False, "errors": exc.messages},
            status=400,
        )

    # Pastikan produk benar-benar tersedia sebelum menyimpannya.
    try:
        product = resolve_product(barcode)
    except ProductSourceUnavailable:
        return JsonResponse(
            {
                "ok": False,
                "errors": [
                    "Sumber produk belum tersedia. "
                    "Silakan coba lagi setelah Discover terhubung."
                ],
            },
            status=503,
        )

    if product is None:
        return JsonResponse(
            {
                "ok": False,
                "errors": ["Produk tidak ditemukan."],
            },
            status=404,
        )

    request.session[SESSION_KEY] = updated_selection

    return JsonResponse(
        {
            "ok": True,
            "barcodes": updated_selection,
            "count": len(updated_selection),
            "can_compare": len(updated_selection) >= 2,
        }
    )
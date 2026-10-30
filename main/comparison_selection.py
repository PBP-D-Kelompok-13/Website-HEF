from django.core.exceptions import ValidationError


MAX_PRODUCTS = 3
MIN_PRODUCTS = 2

def _check_selection(selected):
    """Periksa pilihan tanpa mengubah daftar aslinya."""
    if not isinstance(selected, (list, tuple)):
        raise ValidationError("Pilihan produk harus berupa daftar.")

    products = list(selected)

    for barcode in products:
        if not isinstance(barcode, str) or not barcode.strip():
            raise ValidationError("Identitas produk tidak boleh kosong.")

    if len(products) != len(set(products)):
        raise ValidationError("Produk yang sama tidak boleh dipilih dua kali.")

    if len(products) > MAX_PRODUCTS:
        raise ValidationError("Maksimal tiga produk dapat dipilih.")

    return products

def add_product(selected, barcode):
    """Tambahkan satu produk dan kembalikan daftar pilihan baru."""
    products = _check_selection(selected)

    if not isinstance(barcode, str) or not barcode.strip():
        raise ValidationError("Identitas produk tidak boleh kosong.")

    if barcode in products:
        raise ValidationError("Produk ini sudah dipilih.")

    if len(products) >= MAX_PRODUCTS:
        raise ValidationError(
            "Pilihan sudah penuh. Lepaskan satu produk terlebih dahulu."
        )

    return products + [barcode]


def remove_product(selected, barcode):
    """Lepaskan produk tanpa mengubah daftar pilihan aslinya."""
    products = _check_selection(selected)

    return [
        product_barcode
        for product_barcode in products
        if product_barcode != barcode
    ]


def validate_comparison(selected):
    """Pastikan pilihan siap digunakan untuk membandingkan produk."""
    products = _check_selection(selected)

    if len(products) < MIN_PRODUCTS:
        raise ValidationError(
            "Pilih minimal dua produk berbeda untuk dibandingkan."
        )

    return products
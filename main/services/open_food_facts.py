import os
import requests
from ..models import Product

OFF_API = "https://world.openfoodfacts.org/api/v2/product/{barcode}"
OFF_FIELDS = ",".join(
    [
        "code",
        "product_name",
        "generic_name",
        "brands",
        "quantity",
        "labels",
        "categories_tags",
        "image_url",
        "image_front_url",
        "ecoscore_grade",
        "nutriscore_grade",
        "nutrition_grades",
        "nova_group",
        "nutriments",
        "nutrient_levels",
        "ecoscore_data",
        "origins",
        "packaging",
        "ingredients_text",
        "allergens",
    ]
)

USER_AGENT = os.environ.get(
    "OFF_USER_AGENT",
    "HealthyEcoFoody - Django - Version 1.0 - https://github.com/PBP-D-Kelompok-13/Website-HEF",
)

CATEGORY_RULES = [
    ("Beverages", ("beverage", "drink", "milk", "juice", "water", "tea", "coffee", "plant-based-milk")),
    ("Snacks", ("snack", "chip", "crisp", "biscuit", "chocolate", "cracker", "popcorn", "nut")),
    ("Breakfast", ("breakfast", "cereal", "oat", "muesli", "granola", "yogurt", "spread", "jam")),
    ("Pantry staples", ("pasta", "noodle", "rice", "pulse", "legume", "canned", "sauce", "oil", "flour", "soup")),
]


def _float(value):
    try:
        return round(float(value), 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def _grade(value):
    value = (value or "").strip().lower()
    return value if value in {"a", "b", "c", "d", "e"} else ""


def _level(value):
    value = (value or "").strip().lower()
    return value if value in {"low", "moderate", "high"} else ""


def guess_category(tags):
    joined = " ".join(tags or []).lower()
    for category, keywords in CATEGORY_RULES:
        if any(word in joined for word in keywords):
            return category
    return "Other"


def fetch_and_save_product(barcode, user=None):
    barcode = (barcode or "").strip()
    if not barcode:
        return None
    try:
        response = requests.get(
            OFF_API.format(barcode=barcode),
            params={"fields": OFF_FIELDS},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        return None

    if payload.get("status") != 1 or not payload.get("product"):
        return None

    data = payload["product"]
    nutr = data.get("nutriments") or {}
    levels = data.get("nutrient_levels") or {}
    agri = (data.get("ecoscore_data") or {}).get("agribalyse") or {}
    nova = data.get("nova_group")

    defaults = {
        "name": (data.get("product_name") or data.get("generic_name") or f"Product {barcode}")[:255],
        "brand": ((data.get("brands") or "").split(",")[0].strip())[:255],
        "category": guess_category(data.get("categories_tags")),
        "quantity": (data.get("quantity") or "")[:50],
        "description": data.get("generic_name") or "",
        "image_url": (data.get("image_url") or data.get("image_front_url") or "")[:500],
        "labels": (data.get("labels") or "")[:255],
        "eco_grade": _grade(data.get("ecoscore_grade")),
        "nutri_grade": _grade(data.get("nutriscore_grade") or data.get("nutrition_grades")),
        "nova_group": int(nova) if str(nova) in {"1", "2", "3", "4"} else None,
        "sugars_100g": _float(nutr.get("sugars_100g")),
        "sugars_level": _level(levels.get("sugars")),
        "salt_100g": _float(nutr.get("salt_100g")),
        "salt_level": _level(levels.get("salt")),
        "fat_100g": _float(nutr.get("fat_100g")),
        "fat_level": _level(levels.get("fat")),
        "calories_100g": _float(nutr.get("energy-kcal_100g")),
        "kj_100g": _float(nutr.get("energy-kj_100g") or nutr.get("energy_100g")),
        "fiber_100g": _float(nutr.get("fiber_100g")),
        "co2_kg": _float(agri.get("co2_total")),
        "co2_agriculture": _float(agri.get("co2_agriculture")),
        "co2_processing": _float(agri.get("co2_processing")),
        "co2_packaging": _float(agri.get("co2_packaging")),
        "co2_transport": _float(agri.get("co2_transportation")),
        "origin": (data.get("origins") or "")[:255],
        "packaging": (data.get("packaging") or "")[:255],
        "ingredients": data.get("ingredients_text") or "",
        "allergens": (data.get("allergens") or "").replace("en:", "")[:255],
    }
    product, created = Product.objects.update_or_create(barcode=barcode, defaults=defaults)
    if created and user and getattr(user, "is_authenticated", False):
        product.created_by = user
        product.save(update_fields=["created_by"])
    return product

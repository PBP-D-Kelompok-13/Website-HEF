from unittest.mock import MagicMock, patch
import requests
from django.test import TestCase
from main import services
from main.models import Product
from .factories import make_user

PRODUCT = {
    "code": "3017624010701",
    "product_name": "Nutella",
    "generic_name": "Hazelnut spread",
    "brands": "Ferrero, Other",
    "quantity": "400 g",
    "labels": "Vegetarian, Palm oil",
    "categories_tags": ["en:spreads", "en:sweet-spreads"],
    "image_url": "https://img.test/n.jpg",
    "ecoscore_grade": "d",
    "nutriscore_grade": "e",
    "nova_group": 4,
    "nutriments": {
        "sugars_100g": 56.3,
        "salt_100g": 0.1,
        "fat_100g": 30.9,
        "energy-kcal_100g": 539,
        "energy-kj_100g": 2255,
        "fiber_100g": 0,
    },
    "nutrient_levels": {"sugars": "high", "salt": "low", "fat": "high"},
    "ecoscore_data": {
        "agribalyse": {
            "co2_total": 3.2,
            "co2_agriculture": 2.0,
            "co2_processing": 0.7,
            "co2_packaging": 0.3,
            "co2_transportation": 0.2,
        }
    },
    "origins": "Italy",
    "packaging": "Glass jar",
    "ingredients_text": "Sugar, palm oil",
    "allergens": "en:milk,en:nuts",
}


def ok(product, code="3017624010701"):
    r = MagicMock()
    r.json.return_value = {"status": 1, "code": code, "product": dict(product)}
    return r


class HelperTests(TestCase):
    def test_guess_category(self):
        cases = [
            (["en:beverages"], "Beverages"),
            (["en:salty-snacks"], "Snacks"),
            (["en:breakfast-cereals"], "Breakfast"),
            (["en:pastas"], "Pantry staples"),
            (["en:unknown"], "Other"),
            (None, "Other"),
        ]
        for tags, expected in cases:
            with self.subTest(tags=tags):
                self.assertEqual(services.guess_category(tags), expected)

    def test_grade_and_level_reject_garbage(self):
        for bad in ("unknown", "not-applicable", None, ""):
            self.assertEqual(services._grade(bad), "")
        self.assertEqual(services._level("weird"), "")

    def test_float_coerces_or_returns_none(self):
        self.assertEqual(services._float("3.5"), 3.5)
        self.assertIsNone(services._float("n/a"))
        self.assertIsNone(services._float(None))


@patch("main.services.requests.get")
class FetchAndSaveProductTests(TestCase):
    def test_maps_all_fields(self, get):
        get.return_value = ok(PRODUCT)
        p = services.fetch_and_save_product("3017624010701")
        self.assertEqual((p.name, p.brand, p.category), ("Nutella", "Ferrero", "Breakfast"))
        self.assertEqual((p.eco_grade, p.nutri_grade, p.nova_group), ("d", "e", 4))
        self.assertEqual((p.sugars_100g, p.sugars_level, p.kj_100g), (56.3, "high", 2255))
        self.assertEqual((p.co2_kg, p.co2_agriculture, p.co2_transport), (3.2, 2.0, 0.2))
        self.assertEqual(p.allergens, "milk,nuts")
        self.assertEqual(p.labels, "Vegetarian, Palm oil")

    def test_requests_v2_endpoint_with_user_agent_and_fields(self, get):
        get.return_value = ok(PRODUCT)
        services.fetch_and_save_product("3017624010701")
        self.assertIn("/api/v2/product/3017624010701", get.call_args.args[0])
        self.assertIn("HealthyEcoFoody", get.call_args.kwargs["headers"]["User-Agent"])
        for field in ("ecoscore_data", "categories_tags", "nutrient_levels"):
            self.assertIn(field, get.call_args.kwargs["params"]["fields"])

    def test_not_found_network_error_and_bad_json_return_none(self, get):
        get.return_value = MagicMock(json=MagicMock(return_value={"status": 0}))
        self.assertIsNone(services.fetch_and_save_product("1"))
        get.side_effect = requests.ConnectionError
        self.assertIsNone(services.fetch_and_save_product("1"))
        get.side_effect = None
        get.return_value = MagicMock(json=MagicMock(side_effect=ValueError))
        self.assertIsNone(services.fetch_and_save_product("1"))
        self.assertEqual(Product.objects.count(), 0)

    def test_falls_back_to_nutrition_grades_field(self, get):
        data = dict(PRODUCT)
        del data["nutriscore_grade"]
        data["nutrition_grades"] = "c"
        get.return_value = ok(data)
        self.assertEqual(services.fetch_and_save_product("3017624010701").nutri_grade, "c")

    def test_missing_nested_data_does_not_crash(self, get):
        get.return_value = ok({"product_name": "Plain"}, code="5")
        p = services.fetch_and_save_product("5")
        self.assertIsNone(p.co2_kg)
        self.assertEqual(p.eco_grade, "")

    def test_long_values_are_truncated_for_postgres(self, get):
        get.return_value = ok({"product_name": "x" * 400, "quantity": "y" * 100}, code="6")
        p = services.fetch_and_save_product("6")
        self.assertEqual((len(p.name), len(p.quantity)), (255, 50))

    def test_refetch_updates_instead_of_duplicating(self, get):
        get.return_value = ok({"product_name": "Old"}, code="7")
        services.fetch_and_save_product("7")
        get.return_value = ok({"product_name": "New"}, code="7")
        services.fetch_and_save_product("7")
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Product.objects.get(barcode="7").name, "New")

    def test_owner_is_set_only_on_first_import(self, get):
        first, second = make_user("first"), make_user("second")
        get.return_value = ok({"product_name": "X"}, code="8")
        services.fetch_and_save_product("8", user=first)
        services.fetch_and_save_product("8", user=second)
        self.assertEqual(Product.objects.get(barcode="8").created_by, first)

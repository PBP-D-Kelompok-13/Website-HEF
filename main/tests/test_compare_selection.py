from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from main.comparison_selection import (
    add_product,
    remove_product,
    validate_comparison,
)


class CompareSelectionTests(SimpleTestCase):
    def test_add_product_preserves_existing_selection(self):
        selected = ["001"]

        result = add_product(selected, "002")

        self.assertEqual(result, ["001", "002"])
        self.assertEqual(selected, ["001"])

    def test_duplicate_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            add_product(["001"], "001")

    def test_fourth_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            add_product(["001", "002", "003"], "004")

    def test_empty_barcode_is_rejected(self):
        with self.assertRaises(ValidationError):
            add_product([], "")

    def test_remove_product_preserves_other_products(self):
        selected = ["001", "002", "003"]

        result = remove_product(selected, "002")

        self.assertEqual(result, ["001", "003"])
        self.assertEqual(selected, ["001", "002", "003"])

    def test_removing_unselected_product_leaves_selection_unchanged(self):
        self.assertEqual(
            remove_product(["001", "002"], "003"),
            ["001", "002"],
        )

    def test_two_or_three_different_products_are_valid(self):
        for selected in (
            ["001", "002"],
            ["001", "002", "003"],
        ):
            with self.subTest(selected=selected):
                self.assertEqual(
                    validate_comparison(selected),
                    selected,
                )

    def test_invalid_comparisons_are_rejected(self):
        for selected in (
            [],
            ["001"],
            ["001", "001"],
            ["001", "002", "003", "004"],
            ["001", ""],
        ):
            with self.subTest(selected=selected):
                with self.assertRaises(ValidationError):
                    validate_comparison(selected)
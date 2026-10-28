from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from main.models import Bookmark, Product
from .factories import make_product, make_user


class ProductModelTests(TestCase):
    def test_str_and_absolute_url(self):
        p = make_product(name="Oat Milk", barcode="2000000000018")
        self.assertEqual(str(p), "Oat Milk (2000000000018)")
        self.assertEqual(p.get_absolute_url(), reverse("main:product_detail", args=["2000000000018"]))

    def test_barcode_is_unique(self):
        make_product(barcode="2000000000018")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(barcode="2000000000018")

    def test_optional_fields_default_to_unknown(self):
        p = Product.objects.create(barcode="2000000000019", name="Bare")
        self.assertEqual((p.eco_grade, p.category), ("", "Other"))
        self.assertIsNone(p.co2_kg)

    def test_summaries_fall_back_when_grade_unknown(self):
        self.assertEqual(make_product(eco_grade="a").eco_summary, "Very low environmental impact")
        self.assertEqual(make_product(eco_grade="").eco_summary, "Eco-Score not available")

    def test_label_list_is_trimmed_and_capped_at_three(self):
        p = make_product(labels="Organic, Vegan , ,Fairtrade, Extra")
        self.assertEqual(p.label_list, ["Organic", "Vegan", "Fairtrade"])

    def test_co2_parts_merge_packaging_and_transport(self):
        p = make_product(co2_agriculture=0.2, co2_processing=0.15, co2_packaging=0.06, co2_transport=0.04)
        parts = p.co2_parts
        self.assertEqual([x["label"] for x in parts], ["Growing", "Production", "Packaging & transport"])
        self.assertAlmostEqual(parts[2]["value"], 0.10)
        self.assertAlmostEqual(sum(x["pct"] for x in parts), 100, delta=0.2)

    def test_co2_parts_empty_without_data(self):
        self.assertEqual(make_product().co2_parts, [])

    def test_to_dict_exposes_json_fields(self):
        d = make_product(sugars_100g=2.0).to_dict()
        self.assertEqual(d["nutrition_per_100g"]["sugars"], 2.0)
        self.assertIn("barcode", d)


class ProductQuerySetTests(TestCase):
    def test_search_matches_name_brand_and_barcode_case_insensitively(self):
        a = make_product(name="Almond Drink", brand="Kind Roots")
        make_product(name="Chickpea Crisps", brand="Good Pulse")
        self.assertEqual(list(Product.objects.search("ALMOND")), [a])
        self.assertEqual(list(Product.objects.search("kind")), [a])
        self.assertEqual(list(Product.objects.search(a.barcode)), [a])

    def test_filter_by_category_eco_and_nutri(self):
        target = make_product(category="Snacks", eco_grade="a", nutri_grade="b")
        make_product(category="Beverages", eco_grade="a", nutri_grade="b")
        make_product(category="Snacks", eco_grade="e", nutri_grade="b")
        make_product(category="Snacks", eco_grade="a", nutri_grade="e")
        result = Product.objects.filter_by(category="snacks", eco="a", nutri="b")
        self.assertEqual(list(result), [target])

    def test_invalid_grade_filter_is_ignored(self):
        make_product()
        self.assertEqual(Product.objects.filter_by(eco="zzz").count(), 1)

    def test_filter_by_saved_only_returns_that_users_bookmarks(self):
        user, other = make_user("a"), make_user("b")
        mine, theirs = make_product(), make_product()
        Bookmark.objects.create(user=user, product=mine)
        Bookmark.objects.create(user=other, product=theirs)
        self.assertEqual(list(Product.objects.filter_by(saved_by=user)), [mine])

    def test_sort_by_eco_puts_unknown_grades_last(self):
        e, unknown, a = make_product(eco_grade="e"), make_product(eco_grade=""), make_product(eco_grade="a")
        self.assertEqual(list(Product.objects.filter_by(sort="eco")), [a, e, unknown])

    def test_sort_by_name(self):
        z, a = make_product(name="Zed"), make_product(name="Alpha")
        self.assertEqual(list(Product.objects.filter_by(sort="name")), [a, z])

    def test_with_saved_flag(self):
        user = make_user()
        saved, plain = make_product(), make_product()
        Bookmark.objects.create(user=user, product=saved)
        flags = {p.pk: p.is_saved for p in Product.objects.with_saved_flag(user)}
        self.assertEqual(flags, {saved.pk: True, plain.pk: False})

    def test_with_saved_flag_is_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        make_product()
        self.assertFalse(Product.objects.with_saved_flag(AnonymousUser()).first().is_saved)


class BookmarkModelTests(TestCase):
    def test_one_bookmark_per_user_and_product(self):
        user, p = make_user(), make_product()
        Bookmark.objects.create(user=user, product=p)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Bookmark.objects.create(user=user, product=p)

    def test_deleting_product_cascades_to_bookmarks(self):
        user, p = make_user(), make_product()
        Bookmark.objects.create(user=user, product=p)
        p.delete()
        self.assertEqual(Bookmark.objects.count(), 0)

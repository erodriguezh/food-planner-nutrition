"""Tests for resolve_label(), the label-photo path of alias resolution (#24).

Issue #24: "A label photo produces a Food node ... with no question asked."
The shared resolve_name() asks on a Food-versus-Meal collision. A label photo
carries its own identity (barcode, label name, brand), so resolve_label() must
decide alone and never return `ambiguous` or `none`.

Run: python3 -m unittest discover lint
"""
import inspect
import unittest

from vault_lint import LabelIdentity, resolve_label, resolve_name

# A Food alias and a Meal alias collide on "pudding": resolve_name() asks here.
# The Meal "Porridge" holds a base name a new label may want.
TABLE = [
    ("Protein pudding Migros", "food", ["Proteinpudding", "pudding"]),
    ("Pudding bowl", "meal", ["pudding"]),
    ("Soy milk Alpro", "food", ["Sojadrink Original", "soy milk"]),
    ("Soy milk Migros", "food", ["Sojadrink", "soy milk"]),
    ("Skyr", "food", ["Skyr Natur"]),
    ("Porridge", "meal", ["Haferbrei"]),
]

FOODS = [
    {"name": "Protein pudding Migros", "label_name": "Proteinpudding", "brand": "Migros"},
    {"name": "Soy milk Alpro", "label_name": "Sojadrink Original", "brand": "Alpro"},
    {"name": "Soy milk Migros", "label_name": "Sojadrink", "brand": "Migros"},
    {"name": "Skyr", "label_name": "Skyr Natur", "brand": "Emmi", "barcode": "7610200104007"},
]


class ResolveLabelIdentityTest(unittest.TestCase):
    """Barcode, then label name plus brand, decide before any name matching."""

    def test_a_barcode_match_wins(self):
        label = LabelIdentity(label_name="Skyr Natur Vanille", barcode="7610200104007")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("barcode", "Skyr", "food"))

    def test_the_label_name_and_brand_win_over_a_fuzzy_name(self):
        """"soy milk" is a shared alias, so the name path alone would ask."""
        self.assertEqual(resolve_name("soy milk", TABLE).status, "ambiguous")
        label = LabelIdentity(label_name="Sojadrink Original", brand="Alpro")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("label", "Soy milk Alpro", "food"))

    def test_the_brand_separates_two_foods_with_a_close_label_name(self):
        label = LabelIdentity(label_name="Sojadrink", brand="Migros")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("label", "Soy milk Migros"))

    def test_the_label_identity_is_case_and_umlaut_insensitive(self):
        label = LabelIdentity(label_name="proteinpudding", brand="migros")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("label", "Protein pudding Migros"))


class ResolveLabelNeverAsksTest(unittest.TestCase):
    """The collision the reviewer named: one label name, a Food alias and a
    Meal alias, the Meal in the Pantry. The label must still end in one Food."""

    def test_the_name_path_asks_on_this_collision(self):
        result = resolve_name("pudding", TABLE, pantry_names=["Pudding bowl"])
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)

    def test_the_identified_food_wins_the_collision(self):
        label = LabelIdentity(label_name="Pudding", brand="Migros")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("label", "Protein pudding Migros", "food"))

    def test_an_unidentified_label_becomes_a_new_food_never_the_meal(self):
        label = LabelIdentity(label_name="Pudding", brand="Dr. Oetker")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("new", "Pudding Dr. Oetker", "food"))
        self.assertEqual(result.candidates, ("Protein pudding Migros", "Pudding bowl"))

    def test_no_label_ever_asks(self):
        labels = [
            LabelIdentity(label_name="pudding"),
            LabelIdentity(label_name="soy milk", brand="Coop"),
            LabelIdentity(label_name="Skyr", brand="Emmi"),
            LabelIdentity(label_name="Hühnerbrust"),
            LabelIdentity(label_name="", brand="Alpro"),
        ]
        for label in labels:
            result = resolve_label(label, TABLE, FOODS)
            self.assertNotIn(result.status, ("ambiguous", "none"), label)
            self.assertIsNotNone(result.name, label)
            self.assertEqual(result.kind, "food", label)


class ResolveLabelNewNameTest(unittest.TestCase):
    """No unique Food: a new canonical name that ends with the brand
    (spec #22: "a packaged product ends with the brand")."""

    def test_a_packaged_label_always_ends_with_the_brand(self):
        """The base name is free, and the brand still goes last."""
        label = LabelIdentity(label_name="Quark", brand="Emmi")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("new", "Quark Emmi"))
        self.assertEqual(result.candidates, ())

    def test_a_label_with_no_brand_keeps_the_base_name(self):
        label = LabelIdentity(label_name="Quark")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("new", "Quark"))

    def test_the_brand_is_not_repeated_when_the_label_name_ends_with_it(self):
        label = LabelIdentity(label_name="Sojadrink Alpro", brand="Alpro")
        result = resolve_label(label, [], [])
        self.assertEqual((result.status, result.name), ("new", "Sojadrink Alpro"))

    def test_a_base_name_taken_by_a_meal_is_freed_by_the_brand(self):
        label = LabelIdentity(label_name="Porridge", brand="Emmi")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("new", "Porridge Emmi"))
        self.assertEqual(result.candidates, ("Porridge",))

    def test_a_base_name_taken_with_no_brand_gets_a_free_name(self):
        label = LabelIdentity(label_name="Porridge")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("new", "Porridge 2"))

    def test_a_meal_name_is_never_the_answer(self):
        meals = [name for name, kind, _aliases in TABLE if kind == "meal"]
        for label_name in ("Pudding", "Porridge", "Haferbrei"):
            for brand in (None, "Emmi", "Migros"):
                label = LabelIdentity(label_name=label_name, brand=brand)
                result = resolve_label(label, TABLE, FOODS)
                self.assertNotIn(result.name, meals, (label_name, brand))
                self.assertEqual(result.kind, "food")

    def test_an_empty_vault_creates_the_base_name(self):
        label = LabelIdentity(label_name="Skyr Natur", brand="Emmi")
        result = resolve_label(label, [], [])
        self.assertEqual((result.status, result.name, result.kind), ("new", "Skyr Natur Emmi", "food"))


class ResolveLabelNamePathTest(unittest.TestCase):
    """Without an exact label-name form the alias and fuzzy stages still
    decide, but on the Foods alone and only when one Food is left."""

    def test_one_fuzzy_food_winner_from_the_shared_table_is_used(self):
        """A misread label name matches no form exactly, so the fuzzy stage decides."""
        label = LabelIdentity(label_name="Skyr Naturr")
        result = resolve_label(label, TABLE, [])
        self.assertEqual((result.status, result.name, result.kind), ("label", "Skyr", "food"))

    def test_a_meal_form_is_never_a_label_candidate(self):
        table = [("Pudding", "meal", ["pudding"])]
        label = LabelIdentity(label_name="Pudding", brand="Emmi")
        result = resolve_label(label, table, [])
        self.assertEqual((result.status, result.name, result.kind), ("new", "Pudding Emmi", "food"))

    def test_a_dict_label_is_accepted_like_the_dataclass(self):
        result = resolve_label({"label_name": "Sojadrink Original", "brand": "Alpro"}, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("label", "Soy milk Alpro"))

    def test_a_meal_in_the_foods_list_is_ignored(self):
        foods = FOODS + [{"name": "Pudding bowl", "label_name": "Pudding", "brand": "Emmi", "type": "meal"}]
        label = LabelIdentity(label_name="Pudding", brand="Emmi")
        result = resolve_label(label, TABLE, foods)
        self.assertEqual((result.status, result.name), ("new", "Pudding Emmi"))


class ResolveLabelBrandTest(unittest.TestCase):
    """A printed brand is part of the identity: it may confirm a Food, never
    replace one that carries another brand or no brand at all."""

    GENERIC_TABLE = [("Chicken breast", "food", ["chicken"])]
    GENERIC_FOODS = [{"name": "Chicken breast"}]
    BRANDED_TABLE = [("Chicken breast Migros", "food", [])]
    BRANDED_FOODS = [{"name": "Chicken breast Migros", "label_name": "Chicken breast", "brand": "Migros"}]

    def test_a_branded_label_never_overwrites_a_generic_food(self):
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, self.GENERIC_TABLE, self.GENERIC_FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("new", "Chicken breast Spar", "food"))
        self.assertEqual(result.candidates, ("Chicken breast",))

    def test_a_label_with_no_brand_still_resolves_to_the_generic_food(self):
        label = LabelIdentity(label_name="Chicken breast")
        result = resolve_label(label, self.GENERIC_TABLE, self.GENERIC_FOODS)
        self.assertEqual((result.status, result.name), ("label", "Chicken breast"))

    def test_a_branded_label_never_overwrites_another_brands_food(self):
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, self.BRANDED_TABLE, self.BRANDED_FOODS)
        self.assertEqual((result.status, result.name), ("new", "Chicken breast Spar"))
        self.assertEqual(result.candidates, ("Chicken breast Migros",))

    def test_the_same_brand_food_is_used_even_when_only_the_index_finds_it(self):
        """The Food prints no `label_name`, so the fuzzy stage on the Index
        name decides; the brand on the winner confirms the same product."""
        table = [("Chicken breast Spar", "food", [])]
        foods = [{"name": "Chicken breast Spar", "brand": "Spar"}]
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, table, foods)
        self.assertEqual((result.status, result.name, result.kind), ("label", "Chicken breast Spar", "food"))

    def test_a_branded_label_does_not_take_a_food_of_unknown_brand(self):
        """The Food node was not handed over, so its brand cannot confirm it."""
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, self.GENERIC_TABLE, [])
        self.assertEqual((result.status, result.name), ("new", "Chicken breast Spar"))



class ResolveLabelIgnoresPantryTest(unittest.TestCase):
    """The Pantry is not package identity.

    Ordinary chat resolution may break a same-kind tie by choosing the single
    Pantry candidate. A label photo must not: it overwrites an existing Food
    only when the package identity itself names exactly one Food. Two Foods
    that share the printed name are ambiguous whichever one is in the Pantry.
    """

    # Two Foods share the alias "pudding" and nothing else separates them.
    SHARED_TABLE = [
        ("Pudding Alpha", "food", ["pudding"]),
        ("Pudding Beta", "food", ["pudding"]),
    ]
    SHARED_FOODS = [{"name": "Pudding Alpha"}, {"name": "Pudding Beta"}]

    # Two Foods of one brand share the alias, so the printed brand separates nothing.
    ONE_BRAND_TABLE = [
        ("Pudding Migros 500", "food", ["pudding"]),
        ("Pudding Migros 200", "food", ["pudding"]),
    ]
    ONE_BRAND_FOODS = [
        {"name": "Pudding Migros 500", "label_name": "Pudding", "brand": "Migros"},
        {"name": "Pudding Migros 200", "label_name": "Pudding", "brand": "Migros"},
    ]

    # A misread label name fuzzy-matches one Food and one Meal.
    FUZZY_TABLE = [
        ("Skyr Emmi", "food", ["Skyr Natur"]),
        ("Skyr bowl", "meal", ["Skyr Natur bowl"]),
    ]
    FUZZY_FOODS = [{"name": "Skyr Emmi", "label_name": "Skyr Natur", "brand": "Emmi"}]

    def test_two_foods_share_the_label_name_and_one_is_in_the_pantry(self):
        """The Pantry candidate must not win the label tie."""
        result = resolve_label(LabelIdentity(label_name="Pudding"), self.SHARED_TABLE, self.SHARED_FOODS)
        self.assertEqual((result.status, result.kind), ("new", "food"))
        self.assertNotIn(result.name, ("Pudding Alpha", "Pudding Beta"))

    def test_the_ordinary_name_path_does_use_the_pantry_here(self):
        """The contrast: resolve_name() may still prefer the Pantry candidate."""
        result = resolve_name("Pudding", self.SHARED_TABLE, ["Pudding Alpha"])
        self.assertEqual((result.status, result.name), ("alias", "Pudding Alpha"))

    def test_several_foods_of_the_printed_brand_are_still_ambiguous(self):
        label = LabelIdentity(label_name="Pudding", brand="Migros")
        result = resolve_label(label, self.ONE_BRAND_TABLE, self.ONE_BRAND_FOODS)
        self.assertEqual((result.status, result.kind), ("new", "food"))
        self.assertNotIn(result.name, ("Pudding Migros 500", "Pudding Migros 200"))

    def test_a_fuzzy_food_and_meal_collision_still_identifies_the_food(self):
        """Foods only, so the Meal never blocks the Food the package names."""
        label = LabelIdentity(label_name="Skyr Natu", brand="Emmi")
        result = resolve_label(label, self.FUZZY_TABLE, self.FUZZY_FOODS)
        self.assertEqual((result.status, result.name, result.kind), ("label", "Skyr Emmi", "food"))

    def test_resolve_label_takes_no_pantry_argument(self):
        """The Pantry cannot decide a label, because it is not an input.

        The reviewer's rule, held by the signature: a Pantry list handed over
        by mistake raises instead of breaking a tie in silence.
        """
        self.assertNotIn("pantry_names", inspect.signature(resolve_label).parameters)
        with self.assertRaises(TypeError):
            resolve_label(LabelIdentity(label_name="Pudding"), self.SHARED_TABLE, self.SHARED_FOODS, ["Pudding Alpha"])

    def test_no_label_returns_ambiguous_or_none_or_a_meal(self):
        cases = [
            (self.SHARED_TABLE, self.SHARED_FOODS),
            (self.ONE_BRAND_TABLE, self.ONE_BRAND_FOODS),
            (self.FUZZY_TABLE, self.FUZZY_FOODS),
        ]
        for table, foods in cases:
            meals = [name for name, kind, _aliases in table if kind == "meal"]
            for label_name in ("Pudding", "Skyr Natu", "Skyr Natur bowl", "Quark"):
                for brand in (None, "Migros", "Emmi", "Coop"):
                    label = LabelIdentity(label_name=label_name, brand=brand)
                    result = resolve_label(label, table, foods)
                    self.assertIn(result.status, ("barcode", "label", "new"), (label_name, brand))
                    self.assertEqual(result.kind, "food", (label_name, brand))
                    self.assertNotIn(result.name, meals, (label_name, brand))


if __name__ == "__main__":
    unittest.main()

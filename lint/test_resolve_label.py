"""Tests for resolve_label(), the label-photo path of alias resolution (#24).

Issue #24: "A label photo produces a Food node ... with no question asked."
The shared resolve_name() asks on a Food-versus-Meal collision. A label photo
carries its own identity (barcode, label name, brand), so resolve_label() must
decide alone and never return `ambiguous` or `none`.

Run: python3 -m unittest discover lint
"""
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
        result = resolve_label(label, TABLE, FOODS, pantry_names=["Pudding bowl"])
        self.assertEqual((result.status, result.name, result.kind), ("label", "Protein pudding Migros", "food"))

    def test_an_unidentified_label_becomes_a_new_food_never_the_meal(self):
        label = LabelIdentity(label_name="Pudding", brand="Dr. Oetker")
        result = resolve_label(label, TABLE, FOODS, pantry_names=["Pudding bowl"])
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
            result = resolve_label(label, TABLE, FOODS, pantry_names=["Pudding bowl", "Skyr"])
            self.assertNotIn(result.status, ("ambiguous", "none"), label)
            self.assertIsNotNone(result.name, label)
            self.assertEqual(result.kind, "food", label)


class ResolveLabelNewNameTest(unittest.TestCase):
    """No unique Food: a new canonical name, with the brand as the qualifier
    so the base name is free (spec #22: a packaged product ends with the brand)."""

    def test_a_label_with_no_match_keeps_the_base_name(self):
        label = LabelIdentity(label_name="Quark", brand="Emmi")
        result = resolve_label(label, TABLE, FOODS)
        self.assertEqual((result.status, result.name), ("new", "Quark"))
        self.assertEqual(result.candidates, ())

    def test_a_base_name_taken_by_a_meal_gets_the_brand_qualifier(self):
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
                result = resolve_label(label, TABLE, FOODS, pantry_names=meals)
                self.assertNotIn(result.name, meals, (label_name, brand))
                self.assertEqual(result.kind, "food")

    def test_an_empty_vault_creates_the_base_name(self):
        label = LabelIdentity(label_name="Skyr Natur", brand="Emmi")
        result = resolve_label(label, [], [])
        self.assertEqual((result.status, result.name, result.kind), ("new", "Skyr Natur", "food"))


class ResolveLabelNamePathTest(unittest.TestCase):
    """Without a label identity match the shared table still decides, but only
    when it names one Food."""

    def test_one_fuzzy_food_winner_from_the_shared_table_is_used(self):
        """A misread label name matches no form exactly, so the shared table decides."""
        label = LabelIdentity(label_name="Skyr Naturr")
        result = resolve_label(label, TABLE, [])
        self.assertEqual((result.status, result.name, result.kind), ("fuzzy", "Skyr", "food"))

    def test_a_meal_winner_from_the_shared_table_is_not_used(self):
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
        result = resolve_label(label, TABLE, foods, pantry_names=["Pudding bowl"])
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

    def test_the_same_brand_food_is_used_even_when_only_the_shared_table_finds_it(self):
        """The Food prints no `label_name`, so the shared table decides; the
        brand on the winner confirms it is the same product."""
        table = [("Chicken breast Spar", "food", [])]
        foods = [{"name": "Chicken breast Spar", "brand": "Spar"}]
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, table, foods)
        self.assertEqual((result.status, result.name, result.kind), ("fuzzy", "Chicken breast Spar", "food"))

    def test_a_branded_label_does_not_take_a_food_of_unknown_brand(self):
        """The Food node was not handed over, so its brand cannot confirm it."""
        label = LabelIdentity(label_name="Chicken breast", brand="Spar")
        result = resolve_label(label, self.GENERIC_TABLE, [])
        self.assertEqual((result.status, result.name), ("new", "Chicken breast Spar"))


if __name__ == "__main__":
    unittest.main()

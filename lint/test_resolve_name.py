"""Tests for resolve_name() and its helpers, the shared alias resolution (#24).

Run: python3 -m unittest discover lint
"""
import unittest

from vault_lint import (
    normalize_alias,
    resolve_name,
    parse_alias_table,
)


class AliasResolutionTest(unittest.TestCase):
    TABLE = [
        ("Skyr", "food", ["skyr natur"]),
        ("Blueberries", "food", ["Heidelbeeren", "Blaubeeren"]),
        ("Oats", "food", ["Haferflocken", "oatmeal"]),
        ("Soy milk Alpro", "food", ["Sojadrink Original", "soy milk"]),
        ("Chicken breast", "food", ["Hühnerbrust", "chicken"]),
        ("Chicken meatballs Spar", "food", ["Hühnerfleischbällchen", "meatballs"]),
    ]

    def test_normalize_drops_case_umlauts_and_plurals(self):
        self.assertEqual(normalize_alias("Heidelbeeren"), normalize_alias("heidelbeere"))
        self.assertEqual(normalize_alias("Hühnerbrust"), normalize_alias("huhnerbrust"))
        self.assertEqual(normalize_alias("Eggs"), normalize_alias("egg"))
        self.assertEqual(normalize_alias("Süßkartoffel"), "susskartoffel")

    def test_exact_name_wins(self):
        result = resolve_name("skyr", self.TABLE)
        self.assertEqual((result.status, result.name), ("exact", "Skyr"))

    def test_alias_match_is_case_and_umlaut_insensitive(self):
        result = resolve_name("heidelbeeren", self.TABLE)
        self.assertEqual((result.status, result.name), ("alias", "Blueberries"))
        result = resolve_name("Huhnerbrust", self.TABLE)
        self.assertEqual((result.status, result.name), ("alias", "Chicken breast"))

    def test_plural_tolerant(self):
        result = resolve_name("Blaubeere", self.TABLE)
        self.assertEqual((result.status, result.name), ("alias", "Blueberries"))

    def test_one_fuzzy_candidate_is_used_and_named(self):
        result = resolve_name("Haferflokken", self.TABLE)
        self.assertEqual((result.status, result.name), ("fuzzy", "Oats"))

    def test_no_candidate(self):
        result = resolve_name("Quark", self.TABLE)
        self.assertEqual(result.status, "none")
        self.assertIsNone(result.name)

    def test_several_candidates_ask(self):
        result = resolve_name("Chicken", self.TABLE)
        self.assertEqual(result.status, "alias")  # exact alias "chicken" beats fuzzy
        result = resolve_name("chicken breas", self.TABLE)
        self.assertEqual((result.status, result.name), ("fuzzy", "Chicken breast"))
        result = resolve_name("Hühner", self.TABLE)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), ["Chicken breast", "Chicken meatballs Spar"])

    def test_several_candidates_prefer_pantry(self):
        result = resolve_name("Hühner", self.TABLE, pantry_names=["Chicken breast"])
        self.assertEqual((result.status, result.name), ("fuzzy", "Chicken breast"))

    def test_exact_hit_reports_the_kind_of_the_winner(self):
        result = resolve_name("skyr", self.TABLE)
        self.assertEqual((result.status, result.name, result.kind), ("exact", "Skyr", "food"))
        meal_table = [("Usual breakfast", "meal", ["the usual"])]
        result = resolve_name("usual breakfast", meal_table)
        self.assertEqual((result.status, result.name, result.kind), ("exact", "Usual breakfast", "meal"))
        result = resolve_name("the usual", meal_table)
        self.assertEqual((result.status, result.name, result.kind), ("alias", "Usual breakfast", "meal"))

    def test_parse_alias_table_from_index(self):
        index = (
            "## Food\n- [[Skyr]] | dairy | skyr natur\n- [[Rice]] | grain\n\n"
            "## Meal\n- [[Usual breakfast]] | breakfast | usual, the usual\n\n"
            "## Day\n- 2026-09 | nodes/day/2026-09/\n\n## Goals\n- [[Goals]]\n\n## Pantry\n- [[Pantry]]\n"
        )
        table = parse_alias_table(index)
        self.assertEqual(
            table,
            [("Skyr", "food", ["skyr natur"]), ("Rice", "food", []), ("Usual breakfast", "meal", ["usual", "the usual"])],
        )


class FoodVersusMealCollisionTest(unittest.TestCase):
    """Spec #22: a Food-versus-Meal collision asks. The Pantry preference must
    not break it, because a Pantry item can be a Food or a Meal (a leftover).

    Base names are unique across the vault, so the collision comes from a
    shared alias or from the fuzzy stage. Ticket #25 adds the one exception:
    an explicit slot word makes the Meal win.
    """

    PORRIDGE = [
        ("Porridge", "food", ["oatmeal"]),
        ("Morning porridge", "meal", ["oatmeal"]),
    ]
    BOTH = ["Morning porridge", "Porridge"]

    def test_mixed_collision_asks_when_the_meal_is_in_the_pantry(self):
        result = resolve_name("oatmeal", self.PORRIDGE, pantry_names=["Morning porridge"])
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)
        self.assertIsNone(result.kind)
        self.assertEqual(sorted(result.candidates), self.BOTH)

    def test_mixed_collision_asks_when_the_food_is_in_the_pantry(self):
        result = resolve_name("oatmeal", self.PORRIDGE, pantry_names=["Porridge"])
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)
        self.assertEqual(sorted(result.candidates), self.BOTH)

    def test_mixed_collision_asks_when_neither_is_in_the_pantry(self):
        result = resolve_name("oatmeal", self.PORRIDGE)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), self.BOTH)

    def test_mixed_collision_on_the_exact_stage_asks(self):
        """Normalization can map a Food name and a Meal name to one form."""
        table = [("Egg", "food", []), ("Eggs", "meal", [])]
        result = resolve_name("eggs", table, pantry_names=["Eggs"])
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), ["Egg", "Eggs"])

    def test_mixed_collision_on_the_fuzzy_stage_asks(self):
        table = [("Yoghurt", "food", []), ("Greek yogurt bowl", "meal", [])]
        result = resolve_name("yogurt", table, pantry_names=["Yoghurt"])
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)
        self.assertEqual(sorted(result.candidates), ["Greek yogurt bowl", "Yoghurt"])

    def test_one_kind_only_still_lets_the_pantry_preference_decide(self):
        """Two Meals collide: the Pantry preference still picks the one Meal."""
        table = [("Morning porridge", "meal", ["porridge"]), ("Evening porridge", "meal", ["porridge"])]
        result = resolve_name("porridge", table, pantry_names=["Evening porridge"])
        self.assertEqual((result.status, result.name, result.kind), ("alias", "Evening porridge", "meal"))

    def test_a_single_hit_of_either_kind_needs_no_pantry(self):
        result = resolve_name("oatmeal", [("Morning porridge", "meal", ["oatmeal"])])
        self.assertEqual((result.status, result.name, result.kind), ("alias", "Morning porridge", "meal"))


class NormalizedCollisionTest(unittest.TestCase):
    """Two canonical nodes can collapse to one normalized form. Then the agent asks."""

    PLURAL_TABLE = [
        ("Egg", "food", []),
        ("Eggs", "food", []),
    ]
    UMLAUT_TABLE = [
        ("Hühnchen", "food", []),
        ("Huhnchen", "food", []),
    ]
    ALIAS_TABLE = [
        ("Blueberries", "food", ["Beere"]),
        ("Raspberries", "food", ["Beeren"]),
    ]

    def test_plural_collision_on_exact_stage_asks(self):
        result = resolve_name("eggs", self.PLURAL_TABLE)
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)
        self.assertEqual(sorted(result.candidates), ["Egg", "Eggs"])

    def test_umlaut_collision_on_exact_stage_asks(self):
        result = resolve_name("Hühnchen", self.UMLAUT_TABLE)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), ["Huhnchen", "Hühnchen"])

    def test_plural_collision_prefers_the_pantry_candidate(self):
        result = resolve_name("eggs", self.PLURAL_TABLE, pantry_names=["Eggs"])
        self.assertEqual((result.status, result.name), ("exact", "Eggs"))
        self.assertEqual(sorted(result.candidates), ["Egg", "Eggs"])

    def test_alias_collision_asks(self):
        result = resolve_name("beeren", self.ALIAS_TABLE)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), ["Blueberries", "Raspberries"])

    def test_two_pantry_candidates_still_ask(self):
        result = resolve_name("eggs", self.PLURAL_TABLE, pantry_names=["Egg", "Eggs"])
        self.assertEqual(result.status, "ambiguous")


class FuzzyUnionTest(unittest.TestCase):
    """Fuzzy candidates are the union of close matches and starts-with/contains
    matches. Both candidates here are Foods, so the Pantry preference applies;
    the mixed-kind version of the same union is in FoodVersusMealCollisionTest.
    """

    TABLE = [
        ("Yoghurt", "food", []),
        ("Greek yogurt bowl", "food", []),
    ]

    def test_close_match_and_contains_match_together_ask(self):
        # "yogurt" is a close match of "Yoghurt" only, and it is contained in
        # "Greek yogurt bowl" only. The union holds both, so the agent asks.
        result = resolve_name("yogurt", self.TABLE)
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.name)
        self.assertEqual(sorted(result.candidates), ["Greek yogurt bowl", "Yoghurt"])

    def test_pantry_preference_isolates_one_of_the_union(self):
        result = resolve_name("yogurt", self.TABLE, pantry_names=["Yoghurt"])
        self.assertEqual((result.status, result.name), ("fuzzy", "Yoghurt"))
        self.assertEqual(sorted(result.candidates), ["Greek yogurt bowl", "Yoghurt"])

    def test_exact_name_still_beats_the_fuzzy_union(self):
        result = resolve_name("Yoghurts", self.TABLE)
        self.assertEqual((result.status, result.name), ("exact", "Yoghurt"))


if __name__ == "__main__":
    unittest.main()

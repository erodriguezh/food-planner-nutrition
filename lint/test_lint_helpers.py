"""Tests for the parsing and calculation helpers the lint validates files with (#25).

These are the helpers `lint_vault()` itself calls: the rounding rules, the
ingredient sum behind the Meal totals check, the entry-line parser and the
entry arithmetic behind the Day checks. No routine is run here; what a routine
promises is asserted on the vault files (`test_meal_day.py`) or on the routine
text (`test_routine_contracts_log.py`).

Run: python3 -m unittest discover lint
"""
import unittest
from decimal import Decimal

from test_meal_day import BOWL, BULGUR, RICE, SKYR, BREAKFAST, DINNER, LUNCH, SNACK
from vault_lint import (
    check_entry_shape,
    compute_meal,
    entry_totals,
    matches_rounding,
    parse_entry_line,
    parse_frontmatter,
    resolve_name,
    round_food_value,
    round_total,
    scale_food,
)

FOODS = {name: parse_frontmatter(text)[0] for name, text in (("Skyr", SKYR), ("Rice", RICE), ("Bulgur", BULGUR))}
MEAL = parse_frontmatter(BOWL)[0]


class RoundingRuleTest(unittest.TestCase):
    """Feedback item 2: one rounding rule, applied strictly, a half rounds up."""

    def test_a_whole_number_rounds_half_up(self):
        for exact, want in ((14.49, 14), (14.5, 15), (14.51, 15), (0.5, 1), (37.95, 38), (11.1, 11)):
            with self.subTest(exact=exact):
                self.assertEqual(round_total(exact), want)

    def test_one_decimal_rounds_half_up(self):
        for exact, want in ((1.449, 1.4), (1.45, 1.5), (1.451, 1.5), (2.25, 2.3), (0.35, 0.4)):
            with self.subTest(exact=exact):
                self.assertEqual(round_food_value(exact), want)

    def test_a_whole_result_keeps_no_decimal_point(self):
        self.assertEqual(repr(round_food_value(64.04)), "64")

    def test_a_stored_value_must_be_the_rounded_one(self):
        self.assertTrue(matches_rounding(1, 1.3))
        self.assertFalse(matches_rounding(1.3, 1.3))
        self.assertTrue(matches_rounding(1.5, 1.45, 1))
        self.assertFalse(matches_rounding(1.4, 1.45, 1))


class EntryLineTest(unittest.TestCase):
    """`parse_entry_line()` reads the line the lint checks a Day with."""

    def test_the_four_canonical_shapes_parse(self):
        for line in (BREAKFAST, LUNCH, SNACK, DINNER):
            with self.subTest(line=line):
                self.assertEqual(set(parse_entry_line(line).macros), {"kcal", "protein_g", "fat_g", "carbs_g"})

    def test_parse_reads_the_mark_and_the_change(self):
        entry = parse_entry_line(DINNER)
        self.assertEqual((entry.name, entry.amount, entry.unit, entry.marked), ("Rice bowl", 1.0, "portion", False))
        self.assertEqual(entry.change, ("Skyr", 300.0))
        self.assertEqual(entry.macros, {"kcal": 368, "protein_g": 37, "fat_g": 1, "carbs_g": 51})
        self.assertTrue(parse_entry_line(SNACK).marked)

    def test_a_wrong_shape_raises(self):
        for bad in ("- Rice = 150 g — 528 kcal · 11 P · 1 F · 117 C", "- ~[[Rice]] = 150 g — 528 kcal · 11 P · 1 F · 117 C",
                    "- [[Rice]] = 150 g — 528 kcal, 11 P, 1 F, 117 C", "- [[Rice]] = 150 g"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_entry_line(bad)


class EntryTotalsTest(unittest.TestCase):
    """`entry_totals()` is the arithmetic the Day check compares a line against."""

    def macros(self, *args, **kwargs):
        exact = entry_totals(*args, **kwargs).exact
        return {key: round_total(exact[key]) for key in ("kcal", "protein_g", "fat_g", "carbs_g")}

    def test_a_food_by_grams(self):
        self.assertEqual(self.macros(FOODS["Rice"], 150, "g"), {"kcal": 528, "protein_g": 11, "fat_g": 1, "carbs_g": 117})

    def test_a_meal_by_portion_and_by_grams_agree(self):
        by_portion = self.macros(MEAL, 1, "portion")
        self.assertEqual(by_portion, {"kcal": 240, "protein_g": 15, "fat_g": 1, "carbs_g": 43})
        self.assertEqual(self.macros(MEAL, 150, "g"), by_portion)

    def test_an_entry_never_reports_its_amount_as_a_gram_weight(self):
        """`weight_g` is the ingredient gram sum of a Meal, which `compute_meal()`
        fills. An entry amount may be a portion count, so this field stays 0."""
        self.assertEqual(entry_totals(MEAL, 2, "portion").weight_g, 0.0)
        self.assertEqual(entry_totals(FOODS["Rice"], 150, "g").weight_g, 0.0)

    def test_an_estimate_is_reported_from_the_node(self):
        self.assertTrue(entry_totals(FOODS["Bulgur"], 50, "g").estimated)
        self.assertFalse(entry_totals(FOODS["Rice"], 150, "g").estimated)
        self.assertTrue(entry_totals(dict(MEAL, estimated="true"), 1, "portion").estimated)

    def test_the_changed_amount_is_what_is_on_the_plate(self):
        """Story 45, settled by the owner on PR #31: "usual breakfast with 300 g
        skyr" means 300 g of skyr eaten, whatever the portion count."""
        # Rice bowl lists 200 g Skyr for 2 portions; one portion with the listed 100 g equals the plain line.
        self.assertEqual(self.macros(MEAL, 1, "portion", FOODS, ("Skyr", 100)), self.macros(MEAL, 1, "portion"))
        # A one-portion Meal that lists 200 g: 300 g on the plate adds 100 g of Skyr (64 kcal, 11 P).
        one_portion = dict(MEAL, portions="1")
        whole = self.macros(one_portion, 1, "portion")
        changed = self.macros(one_portion, 1, "portion", FOODS, ("Skyr", 300))
        self.assertEqual((changed["kcal"] - whole["kcal"], changed["protein_g"] - whole["protein_g"]), (64, 11))
        self.assertEqual(self.macros(MEAL, 1, "portion", FOODS, ("Skyr", 300))["kcal"], 368)

    def test_a_food_is_logged_in_grams(self):
        with self.assertRaises(ValueError):
            entry_totals(FOODS["Rice"], 1, "portion")

    def test_an_ingredient_change_needs_a_meal_by_portion_and_a_listed_food(self):
        with self.assertRaises(ValueError):
            entry_totals(FOODS["Rice"], 150, "g", FOODS, ("Skyr", 100))
        with self.assertRaises(ValueError):
            entry_totals(MEAL, 150, "g", FOODS, ("Skyr", 300))
        with self.assertRaises(ValueError):
            entry_totals(MEAL, 1, "portion", FOODS, ("Bulgur", 300))


class EntryShapeTest(unittest.TestCase):
    """`check_entry_shape()` is the part of the entry rules that no later change to
    a node can undo, so the Day check applies it to a closed Day as well (PR #31).
    """

    def test_the_canonical_shapes_pass(self):
        check_entry_shape("food", "Rice", "g")
        check_entry_shape("meal", "Rice bowl", "portion")
        check_entry_shape("meal", "Rice bowl", "g")
        check_entry_shape("meal", "Rice bowl", "portion", ("Skyr", 300), "food")

    def test_a_food_is_logged_in_grams_and_carries_no_change(self):
        with self.assertRaises(ValueError):
            check_entry_shape("food", "Rice", "portion")
        with self.assertRaises(ValueError):
            check_entry_shape("food", "Rice", "g", ("Skyr", 300), "food")

    def test_an_ingredient_change_is_a_meal_by_portion(self):
        with self.assertRaises(ValueError):
            check_entry_shape("meal", "Rice bowl", "g", ("Skyr", 300), "food")

    def test_an_unresolved_changed_link_is_left_to_the_vault_path(self):
        """PR #31 review: `entry_totals()` does not look the changed link up, because
        its `foods` holds Food nodes only and a Meal link would look missing there.
        The type of an unresolved link is left unjudged, so no caller of
        `entry_totals()` ever hears that the link "does not exist"; the Day check
        resolves it against every node and judges it.
        """
        check_entry_shape("meal", "Rice bowl", "portion", ("Quark", 300))
        with self.assertRaisesRegex(ValueError, "is not an ingredient of"):
            entry_totals(MEAL, 1, "portion", FOODS, ("Quark", 300))

    def test_the_changed_link_is_a_food(self):
        with self.assertRaises(ValueError):
            check_entry_shape("meal", "Rice bowl", "portion", ("Quark", 300), None)
        with self.assertRaises(ValueError):
            check_entry_shape("meal", "Rice bowl", "portion", ("Rice bowl", 300), "meal")


class ComputeMealTest(unittest.TestCase):
    """`compute_meal()` is the sum the Meal totals check compares against."""

    def test_compute_meal_sums_the_food_nodes(self):
        """The sum is decimal, so 22 + 7.4 is exactly 29.4 and not a float near it."""
        totals = compute_meal(MEAL["ingredients"], FOODS)
        self.assertEqual(totals.weight_g, 300)
        self.assertEqual(totals.exact["kcal"], Decimal("480"))
        self.assertEqual(totals.exact["protein_g"], Decimal("29.4"))
        self.assertEqual(totals.exact["sugar_g"], Decimal("8.2"))
        self.assertFalse(totals.estimated)

    def test_an_estimate_ingredient_makes_the_meal_estimated(self):
        self.assertTrue(compute_meal(["[[Skyr]] = 200 g", "[[Bulgur]] = 100 g"], FOODS).estimated)

    def test_compute_meal_names_a_missing_food(self):
        with self.assertRaises(KeyError):
            compute_meal(["[[Quark]] = 100 g"], FOODS)


def _food(name, macro, nutrient):
    """A Food node as the frontmatter parser gives it: every value a string."""
    return dict(
        {"type": "food", "name": name, "number_source": "database"},
        **{f"{key}_per_100g": str(macro) for key in ("kcal", "protein_g", "fat_g", "carbs_g")},
        **{f"{key}_per_100g": str(nutrient) for key in ("fiber_g", "sugar_g", "salt_g")},
    )


class HalfFromMultiplicationTest(unittest.TestCase):
    """Round-3 feedback item 1: the half that decides the rounding is produced
    by the multiplication, so the multiplication itself must be decimal.

    9.2 per 100 g times 375 g is exactly 34.5 and must store 35; as a binary
    float it is 34.49999999999999 and rounds down to 34. 0.7 per 100 g times
    350 g is exactly 2.45 and must store 2.5; as a float it is
    2.4499999999999997 and rounds down to 2.4.
    """

    # 9.2 per 100 g of every macro, 0.7 per 100 g of every nutrient.
    HALF_MAKER = _food("Half maker", 9.2, 0.7)
    # 1 per 100 g of all seven, so 1000 g give exactly 10 of each.
    TEST_UNIT = _food("Test unit", 1, 1)
    FOODS = {"Half maker": HALF_MAKER, "Test unit": TEST_UNIT}

    def test_a_whole_number_half_comes_out_of_the_multiplication(self):
        exact = scale_food(self.HALF_MAKER, 375)["kcal"]
        self.assertEqual(round_total(exact), 35)
        self.assertTrue(matches_rounding(35, exact))
        self.assertFalse(matches_rounding(34, exact))

    def test_a_one_decimal_half_comes_out_of_the_multiplication(self):
        exact = scale_food(self.HALF_MAKER, 350)["fiber_g"]
        self.assertEqual(round_food_value(exact), 2.5)
        self.assertTrue(matches_rounding(2.5, exact, 1))
        self.assertFalse(matches_rounding(2.4, exact, 1))

    def test_a_multi_ingredient_sum_lands_on_a_half(self):
        totals = compute_meal(["[[Half maker]] = 375 g", "[[Test unit]] = 1000 g"], self.FOODS)
        # 34.5 kcal plus 10 kcal is exactly 44.5.
        self.assertEqual(round_total(totals.exact["kcal"]), 45)
        self.assertTrue(matches_rounding(45, totals.exact["kcal"]))
        self.assertEqual(totals.weight_g, 1375)

    def test_an_entry_of_a_food_by_grams_lands_on_a_half(self):
        totals = entry_totals(self.HALF_MAKER, 375, "g")
        self.assertEqual(round_total(totals.exact["kcal"]), 35)
        self.assertEqual(round_food_value(entry_totals(self.HALF_MAKER, 350, "g").exact["fiber_g"]), 2.5)

    def test_a_meal_total_is_multiplied_before_it_is_divided(self):
        """121 kcal over 22 portions is exactly 5.5 and stores 6. A factor
        computed first is 1 / 22 in 28 digits, and 121 times it gives
        5.499999999999999999999999999, which stores 5."""
        meal = {"type": "meal", "name": "Portion meal", "portions": "22", "weight_g": "12100",
                "kcal": "121", "protein_g": "121", "fat_g": "121", "carbs_g": "121",
                "fiber_g": "121", "sugar_g": "121", "salt_g": "121", "estimated": "false"}
        self.assertEqual(entry_totals(meal, 1, "portion").exact["kcal"], Decimal("5.5"))
        self.assertEqual(round_total(entry_totals(meal, 1, "portion").exact["kcal"]), 6)
        self.assertEqual(round_total(entry_totals(meal, 550, "g").exact["kcal"]), 6)

    def test_an_entry_of_a_meal_by_portion_lands_on_a_half(self):
        """The portions division stays decimal too: 69 kcal over 2 portions is 34.5."""
        meal = {"type": "meal", "name": "Half meal", "portions": "2", "weight_g": "750",
                "kcal": "69", "protein_g": "69", "fat_g": "69", "carbs_g": "69",
                "fiber_g": "4.9", "sugar_g": "4.9", "salt_g": "4.9", "estimated": "false"}
        totals = entry_totals(meal, 1, "portion")
        self.assertEqual(round_total(totals.exact["kcal"]), 35)
        self.assertEqual(round_total(entry_totals(meal, 375, "g").exact["kcal"]), 35)


class SlotWordMakesTheMealWinTest(unittest.TestCase):
    """Story 49 and spec #22: a Food-versus-Meal collision asks, except when
    the log carries a slot word; then the Meal wins."""

    PORRIDGE = [("Porridge", "food", ["oatmeal"]), ("Morning porridge", "meal", ["oatmeal"])]

    def test_without_a_slot_word_the_collision_asks(self):
        self.assertEqual(resolve_name("oatmeal", self.PORRIDGE).status, "ambiguous")

    def test_with_a_slot_word_the_meal_wins(self):
        result = resolve_name("oatmeal", self.PORRIDGE, slot_word=True)
        self.assertEqual((result.status, result.name, result.kind), ("alias", "Morning porridge", "meal"))

    def test_the_slot_word_does_not_decide_between_two_meals(self):
        table = self.PORRIDGE + [("Evening porridge", "meal", ["oatmeal"])]
        result = resolve_name("oatmeal", table, slot_word=True)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(sorted(result.candidates), ["Evening porridge", "Morning porridge"])
        result = resolve_name("oatmeal", table, pantry_names=["Evening porridge"], slot_word=True)
        self.assertEqual((result.status, result.name), ("alias", "Evening porridge"))

    def test_the_slot_word_changes_nothing_when_only_foods_match(self):
        table = [("Porridge", "food", ["oatmeal"]), ("Oat porridge", "food", ["oatmeal"])]
        self.assertEqual(resolve_name("oatmeal", table, slot_word=True).status, "ambiguous")
        self.assertEqual(resolve_name("porridge", table, slot_word=True).name, "Porridge")


if __name__ == "__main__":
    unittest.main()

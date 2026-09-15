"""Tests for the log, rebalance and create-meal routines as functions (#25).

Run: python3 -m unittest discover lint
"""
import unittest

from test_meal_day import BOWL, BULGUR, RICE, SKYR, BREAKFAST, LUNCH, SNACK, DINNER
from vault_lint import (
    Entry,
    build_meal,
    compute_meal,
    day_totals,
    entry_totals,
    format_entry_line,
    log_entry,
    meal_index_line,
    open_slots,
    over_max,
    parse_entry_line,
    parse_frontmatter,
    pick_slot,
    remaining,
    resolve_name,
    round_total,
)

FOODS = {name: parse_frontmatter(text)[0] for name, text in (("Skyr", SKYR), ("Rice", RICE), ("Bulgur", BULGUR))}
MEAL = parse_frontmatter(BOWL)[0]
GOALS = {"kcal": "2500", "protein_g": "135", "fat_g": "60", "carbs_g": "355",
         "kcal_max": "2625", "protein_g_max": "142", "fat_g_max": "63", "carbs_g_max": "373"}


class SlotRuleTest(unittest.TestCase):
    """Story 50: the user's word, else the clock, else the next slot in order."""

    def test_the_word_wins_over_the_clock(self):
        self.assertEqual(pick_slot("snack", "08:30"), "snack")
        self.assertEqual(pick_slot("Dinner", "08:30", filled=["dinner"]), "dinner")

    def test_a_word_that_is_not_a_slot_fails(self):
        with self.assertRaises(ValueError):
            pick_slot("brunch", "10:00")

    def test_the_clock_boundaries(self):
        for clock, slot in (("06:00", "breakfast"), ("10:59", "breakfast"), ("11:00", "lunch"), ("14:59", "lunch"),
                            ("15:00", "snack"), ("17:59", "snack"), ("18:00", "dinner"), ("23:30", "dinner")):
            with self.subTest(clock=clock):
                self.assertEqual(pick_slot(None, clock), slot)

    def test_a_filled_clock_slot_moves_to_the_next_slot_in_order(self):
        # Spec #22 fixes the order breakfast, lunch, snack, dinner, so the slot
        # after a filled breakfast is lunch; the "10:15 croissant under Snack"
        # example of story 50 does not follow from that order (see the PR).
        self.assertEqual(pick_slot(None, "10:15", filled=["breakfast"]), "lunch")
        self.assertEqual(pick_slot(None, "10:15", filled=["breakfast", "lunch"]), "snack")
        self.assertEqual(pick_slot(None, "16:00", filled=["snack"]), "dinner")

    def test_a_filled_dinner_stays_dinner(self):
        self.assertEqual(pick_slot(None, "21:00", filled=["dinner"]), "dinner")

    def test_no_word_and_no_clock_fails(self):
        with self.assertRaises(ValueError):
            pick_slot(None, None)

    def test_open_slots_in_order_minus_the_removed_ones(self):
        self.assertEqual(open_slots(filled=["breakfast"], removed=["snack"]), ["lunch", "dinner"])
        self.assertEqual(open_slots(filled=[]), ["breakfast", "lunch", "snack", "dinner"])


class EntryLineTest(unittest.TestCase):
    def test_round_trip_of_the_four_canonical_shapes(self):
        for line in (BREAKFAST, LUNCH, SNACK, DINNER):
            self.assertEqual(format_entry_line(parse_entry_line(line)), line)

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

    def test_a_food_entry_from_its_node(self):
        entry = log_entry(FOODS["Rice"], 150, "g")
        self.assertEqual(format_entry_line(entry), LUNCH)

    def test_an_estimated_food_carries_the_mark(self):
        entry = log_entry(FOODS["Bulgur"], 50, "g")
        self.assertEqual(format_entry_line(entry), SNACK)

    def test_a_guessed_amount_carries_the_mark(self):
        entry = log_entry(FOODS["Rice"], 150, "g", guessed=True)
        self.assertEqual(format_entry_line(entry), "- ~ " + LUNCH[2:])

    def test_a_meal_by_portion_and_by_grams(self):
        self.assertEqual(format_entry_line(log_entry(MEAL, 1, "portion")), BREAKFAST)
        self.assertEqual(format_entry_line(log_entry(MEAL, 150, "g")), BREAKFAST.replace("1 portion", "150 g"))

    def test_an_ingredient_change_recomputes_from_the_meal_and_the_food(self):
        entry = log_entry(MEAL, 1, "portion", foods=FOODS, change=("Skyr", 300))
        self.assertEqual(format_entry_line(entry), DINNER)

    def test_the_changed_amount_is_what_is_on_the_plate(self):
        """Story 45: "usual breakfast with 300 g skyr" means 300 g of skyr eaten, whatever the portion count."""
        one_portion = dict(MEAL, portions="1")
        two_portions = log_entry(MEAL, 1, "portion", foods=FOODS, change=("Skyr", 300)).macros
        # Rice bowl lists 200 g Skyr for 2 portions; one portion with the listed 100 g equals the plain line.
        self.assertEqual(log_entry(MEAL, 1, "portion", foods=FOODS, change=("Skyr", 100)).macros, log_entry(MEAL, 1, "portion").macros)
        # A one-portion Meal that lists 200 g: 300 g on the plate adds 100 g of Skyr (64 kcal, 11 P).
        whole = log_entry(one_portion, 1, "portion").macros
        changed = log_entry(one_portion, 1, "portion", foods=FOODS, change=("Skyr", 300)).macros
        self.assertEqual((changed["kcal"] - whole["kcal"], changed["protein_g"] - whole["protein_g"]), (64, 11))
        self.assertEqual(two_portions["kcal"], 368)

    def test_an_estimated_meal_carries_the_mark(self):
        meal = dict(MEAL, estimated="true")
        self.assertTrue(log_entry(meal, 1, "portion").marked)

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

    def test_round_total_is_whole_and_half_up(self):
        self.assertEqual(round_total(14.5), 15)
        self.assertEqual(round_total(0.5), 1)
        self.assertEqual(round_total(37.95), 38)
        self.assertEqual(round_total(11.1), 11)


class DayTotalsTest(unittest.TestCase):
    def test_totals_sum_the_lines_and_bubble_the_mark(self):
        entries = [parse_entry_line(line) for line in (BREAKFAST, LUNCH, SNACK, DINNER)]
        nutrients = [entry_totals(MEAL, 1, "portion").exact, entry_totals(FOODS["Rice"], 150, "g").exact,
                     entry_totals(FOODS["Bulgur"], 50, "g").exact, entry_totals(MEAL, 1, "portion", FOODS, ("Skyr", 300)).exact]
        totals = day_totals(entries, nutrients)
        self.assertEqual((totals["kcal"], totals["protein_g"], totals["fat_g"], totals["carbs_g"]), (1307, 69, 4, 249))
        self.assertEqual((totals["fiber_g"], totals["sugar_g"], totals["salt_g"]), (8.8, 16.7, 0.4))
        self.assertEqual(totals["estimated"], "true")

    def test_no_marked_line_means_not_estimated(self):
        totals = day_totals([parse_entry_line(LUNCH)], [entry_totals(FOODS["Rice"], 150, "g").exact])
        self.assertEqual(totals["estimated"], "false")
        self.assertEqual(totals["kcal"], 528)


class RebalanceTest(unittest.TestCase):
    def test_remaining_is_target_minus_running_totals(self):
        day = {"kcal": "428", "protein_g": "34", "fat_g": "7", "carbs_g": "56"}
        self.assertEqual(remaining(GOALS, day), {"kcal": 2072, "protein_g": 101, "fat_g": 53, "carbs_g": 299})

    def test_remaining_of_an_empty_day_is_the_target(self):
        self.assertEqual(remaining(GOALS, {}), {"kcal": 2500, "protein_g": 135, "fat_g": 60, "carbs_g": 355})

    def test_over_max_names_the_macros_above_the_stored_max(self):
        self.assertEqual(over_max(GOALS, {"kcal": "2700", "protein_g": "100", "fat_g": "64", "carbs_g": "300"}), ["kcal", "fat_g"])
        self.assertEqual(over_max(GOALS, {"kcal": "2625"}), [])


class CreateMealTest(unittest.TestCase):
    def test_compute_meal_sums_the_food_nodes(self):
        totals = compute_meal(MEAL["ingredients"], FOODS)
        self.assertEqual(totals.weight_g, 300)
        self.assertAlmostEqual(totals.exact["kcal"], 480)
        self.assertAlmostEqual(totals.exact["protein_g"], 29.4)
        self.assertAlmostEqual(totals.exact["sugar_g"], 8.2)
        self.assertFalse(totals.estimated)

    def test_build_meal_writes_the_stored_shape(self):
        data = build_meal("Rice bowl", MEAL["ingredients"], FOODS, "2026-09-15", portions=2, slots=["lunch", "dinner"], aliases=["the bowl"], reviewed=True)
        self.assertEqual({k: v if isinstance(v, list) else str(v) for k, v in data.items()}, MEAL)
        self.assertEqual(list(data), list(MEAL))

    def test_build_meal_is_unreviewed_before_the_ok_and_estimated_with_an_estimate(self):
        data = build_meal("Bulgur bowl", ["[[Skyr]] = 200 g", "[[Bulgur]] = 100 g"], FOODS, "2026-09-15")
        self.assertEqual((data["reviewed"], data["estimated"], data["portions"]), ("false", "true", 1))
        self.assertEqual((data["kcal"], data["protein_g"], data["fat_g"], data["carbs_g"]), (470, 34, 2, 84))
        self.assertNotIn("slots", data)
        self.assertNotIn("aliases", data)

    def test_compute_meal_names_a_missing_food(self):
        with self.assertRaises(KeyError):
            compute_meal(["[[Quark]] = 100 g"], FOODS)

    def test_meal_index_line(self):
        self.assertEqual(meal_index_line(MEAL), "- [[Rice bowl]] | lunch, dinner | the bowl")
        self.assertEqual(meal_index_line({"name": "Chili"}), "- [[Chili]] | any")


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

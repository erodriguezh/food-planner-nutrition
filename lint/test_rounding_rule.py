"""Tests for the strict rounding rule on the vault files (#25, feedback item 2).

One Food whose seven per-100-g values are all 1, so `n` grams give exactly
n / 100 of every total. The Meal built from it puts the stored totals on the
rounding boundary, which is what the lint compares against.

The second half of the file is round-3 feedback item 1: a Food whose values
make the arithmetic itself land on a half (9.2 and 0.7 per 100 g). Those
halves only survive decimal arithmetic; in binary floats they arrive just
under the half and round the wrong way.

Run: python3 -m unittest discover lint
"""
import unittest

from test_meal_day import LintCase, OPEN_STATE
from test_vault_lint import VaultFixture, INDEX

# One Food whose seven per-100-g values are all 1, so `n` grams give exactly
# n / 100 of every total. It makes the rounding boundaries readable.
UNIT = """---
type: food
name: Test unit
category: snack
kcal_per_100g: 1
protein_g_per_100g: 1
fat_g_per_100g: 1
carbs_g_per_100g: 1
fiber_g_per_100g: 1
sugar_g_per_100g: 1
salt_g_per_100g: 1
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""

UNIT_INDEX = INDEX.replace("## Food\n", "## Food\n- [[Test unit]] | snack\n").replace(
    "## Meal\n", "## Meal\n- [[Unit meal]] | any\n")


def meal_node(name, ingredients, macro, nutrient, weight, portions=1):
    """A Meal with the ingredients and stored totals given. One builder for
    every Meal fixture in this file."""
    items = "".join(f'  - "{item}"\n' for item in ingredients)
    return (
        "---\n"
        "type: meal\n"
        f"name: {name}\n"
        "ingredients:\n"
        f"{items}"
        f"portions: {portions}\n"
        f"weight_g: {weight}\n"
        f"kcal: {macro}\n"
        f"protein_g: {macro}\n"
        f"fat_g: {macro}\n"
        f"carbs_g: {macro}\n"
        f"fiber_g: {nutrient}\n"
        f"sugar_g: {nutrient}\n"
        f"salt_g: {nutrient}\n"
        "totals_date: 2026-09-15\n"
        "estimated: false\n"
        "reviewed: true\n"
        "---\n"
    )


def unit_meal(grams, macro, nutrient, weight=None):
    """A one-ingredient Meal of `grams` of Test unit with the stored totals given."""
    return meal_node("Unit meal", [f"[[Test unit]] = {grams} g"], macro, nutrient,
                     grams if weight is None else weight)


class UnitFixture(VaultFixture):
    def __init__(self):
        super().__init__()
        self.write("nodes/food/Test unit.md", UNIT)
        self.write("index.md", UNIT_INDEX)


class StrictRoundingTest(LintCase):
    """Feedback item 2: a stored total equals the exact value rounded half-up,
    whole for kcal, protein, fat and carbs, one decimal for fiber, sugar and salt."""

    fixture = UnitFixture

    def meal(self, grams, macro, nutrient, weight=None):
        self.vault.write("nodes/meal/Unit meal.md", unit_meal(grams, macro, nutrient, weight))

    def test_the_whole_number_boundary(self):
        # 149 g give 1.49 of every total, 150 g give 1.50, 151 g give 1.51.
        for grams, macro in ((149, 1), (150, 2), (151, 2)):
            with self.subTest(grams=grams):
                self.meal(grams, macro, 1.5)
                self.assertClean()

    def test_a_whole_number_off_the_boundary_fails(self):
        for grams, wrong in ((149, 2), (150, 1), (151, 1)):
            with self.subTest(grams=grams):
                self.meal(grams, wrong, 1.5)
                self.assertError("kcal")

    def test_the_one_decimal_boundary(self):
        # 144.9 g give 1.449 of every total, 145 g give 1.450, 145.1 g give 1.451.
        for grams, nutrient in ((144.9, 1.4), (145, 1.5), (145.1, 1.5)):
            with self.subTest(grams=grams):
                self.meal(grams, 1, nutrient)
                self.assertClean()

    def test_a_one_decimal_value_off_the_boundary_fails(self):
        for grams, wrong in ((144.9, 1.5), (145, 1.4), (145.1, 1.4)):
            with self.subTest(grams=grams):
                self.meal(grams, 1, wrong)
                self.assertError("fiber_g")

    def test_an_unrounded_total_fails(self):
        """Feedback item 2: the old tolerance accepted any value within half a
        unit, so an exact 1.49 could be stored unrounded."""
        self.meal(149, 1.49, 1.5)
        self.assertError("kcal")

    # --- weight_g is never rounded (feedback item 3) ---------------------

    def test_fractional_grams_keep_the_exact_weight(self):
        self.meal(33.3, 0, 0.3)
        self.assertClean()

    def test_a_rounded_weight_fails(self):
        self.meal(33.3, 0, 0.3, weight=33)
        self.assertError("weight_g")


# 9.2 per 100 g of every macro and 0.7 per 100 g of every nutrient. Both make a
# half out of the multiplication alone: 9.2 x 375 / 100 = 34.5 exactly and
# 0.7 x 350 / 100 = 2.45 exactly. In binary floats they are 34.49999999999999
# and 2.4499999999999997, which round the wrong way.
HALF_MAKER = """---
type: food
name: Half maker
category: snack
kcal_per_100g: 9.2
protein_g_per_100g: 9.2
fat_g_per_100g: 9.2
carbs_g_per_100g: 9.2
fiber_g_per_100g: 0.7
sugar_g_per_100g: 0.7
salt_g_per_100g: 0.7
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""

HALF_INDEX = INDEX.replace(
    "## Food\n", "## Food\n- [[Half maker]] | snack\n- [[Test unit]] | snack\n").replace(
    "## Meal\n", "## Meal\n- [[Half meal]] | any\n").replace(
    "## Day\n", "## Day\n- 2026-09 | nodes/day/2026-09/\n")


def half_meal(ingredients, macro, nutrient, weight, portions=1):
    """A Meal named Half meal with the ingredients and stored totals given."""
    return meal_node("Half meal", ingredients, macro, nutrient, weight, portions)


def half_day(line, macro, nutrient):
    """An open Day whose one entry line is the Half maker."""
    return (
        "---\n"
        "type: day\n"
        "name: 2026-09-15\n"
        "date: 2026-09-15\n"
        "status: open\n"
        'goal: "[[Goals]]"\n'
        f"kcal: {macro}\n"
        f"protein_g: {macro}\n"
        f"fat_g: {macro}\n"
        f"carbs_g: {macro}\n"
        f"fiber_g: {nutrient}\n"
        f"sugar_g: {nutrient}\n"
        f"salt_g: {nutrient}\n"
        "estimated: false\n"
        "---\n"
        "\n"
        "## Breakfast\n"
        "\n"
        f"{line}\n"
    )


class HalfMakerFixture(UnitFixture):
    """The unit vault plus the Half maker Food, one Meal of it and one open Day
    of it. Every total is the half-up value of the exact decimal arithmetic, so
    the fixture is clean and each test rewrites the one node it is about."""

    def __init__(self):
        super().__init__()
        self.write("nodes/food/Half maker.md", HALF_MAKER)
        self.write("nodes/meal/Half meal.md", half_meal(["[[Half maker]] = 375 g"], 35, 2.6, 375))
        self.write("nodes/day/2026-09/2026-09-15.md",
                   half_day("- [[Half maker]] = 375 g — 35 kcal · 35 P · 35 F · 35 C", 35, 2.6))
        self.write("index.md", HALF_INDEX)
        self.write("state.md", OPEN_STATE)


class HalfProducedByMultiplicationTest(LintCase):
    """Round-3 feedback item 1: a half the multiplication produces must round up.

    The lint reads the stored decimal numbers, scales and sums them as
    decimals, and only then rounds half up. Float arithmetic turns 34.5 into
    34.49999999999999 and rounds it down, which these fixtures catch.
    """

    fixture = HalfMakerFixture

    def meal(self, ingredients, macro, nutrient, weight, portions=1):
        self.vault.write("nodes/meal/Half meal.md", half_meal(ingredients, macro, nutrient, weight, portions))

    def day(self, line, macro, nutrient):
        self.vault.write("nodes/day/2026-09/2026-09-15.md", half_day(line, macro, nutrient))

    # --- one ingredient -------------------------------------------------

    def test_a_meal_kcal_half_rounds_up(self):
        # 9.2 x 375 / 100 = 34.5 kcal -> 35; the nutrients give 2.625 -> 2.6.
        self.meal(["[[Half maker]] = 375 g"], 35, 2.6, 375)
        self.assertClean()

    def test_a_meal_kcal_half_rounded_down_fails(self):
        self.meal(["[[Half maker]] = 375 g"], 34, 2.6, 375)
        self.assertError("kcal")

    def test_a_meal_nutrient_half_rounds_up(self):
        # 0.7 x 350 / 100 = 2.45 fiber -> 2.5; the macros give 32.2 -> 32.
        self.meal(["[[Half maker]] = 350 g"], 32, 2.5, 350)
        self.assertClean()

    def test_a_meal_nutrient_half_rounded_down_fails(self):
        self.meal(["[[Half maker]] = 350 g"], 32, 2.4, 350)
        self.assertError("fiber_g")

    # --- several ingredients --------------------------------------------

    def test_a_multi_ingredient_sum_that_lands_on_a_half_rounds_up(self):
        # 34.5 kcal from the Half maker plus 10 kcal from 1000 g of Test unit
        # (1 per 100 g) is exactly 44.5 -> 45. The nutrients give 12.625 -> 12.6.
        self.meal(["[[Half maker]] = 375 g", "[[Test unit]] = 1000 g"], 45, 12.6, 1375)
        self.assertClean()

    def test_a_multi_ingredient_half_rounded_down_fails(self):
        self.meal(["[[Half maker]] = 375 g", "[[Test unit]] = 1000 g"], 44, 12.6, 1375)
        self.assertError("kcal")

    # --- a Day entry line -----------------------------------------------

    def test_an_entry_line_macro_half_rounds_up(self):
        self.day("- [[Half maker]] = 375 g — 35 kcal · 35 P · 35 F · 35 C", 35, 2.6)
        self.assertClean()

    def test_an_entry_line_macro_half_rounded_down_fails(self):
        self.day("- [[Half maker]] = 375 g — 34 kcal · 34 P · 34 F · 34 C", 34, 2.6)
        self.assertError("kcal")

    def test_an_open_day_nutrient_half_rounds_up(self):
        self.day("- [[Half maker]] = 350 g — 32 kcal · 32 P · 32 F · 32 C", 32, 2.5)
        self.assertClean()

    def test_an_open_day_nutrient_half_rounded_down_fails(self):
        self.day("- [[Half maker]] = 350 g — 32 kcal · 32 P · 32 F · 32 C", 32, 2.4)
        self.assertError("fiber_g")

    # --- a Meal by portion ----------------------------------------------

    def test_a_portion_of_a_meal_multiplies_before_it_divides(self):
        """121 kcal over 22 portions is exactly 5.5, so one portion stores 6.

        A factor computed first is 1 / 22 rounded to the 28 digits of the
        default precision, and 121 times it gives 5.499999999999999999999999999,
        which stores 5. So the total is multiplied before it is divided.
        """
        # 12100 g of Test unit (1 per 100 g) give exactly 121 of all seven totals.
        self.meal(["[[Test unit]] = 12100 g"], 121, 121, 12100, portions=22)
        self.day("- [[Half meal]] = 1 portion — 6 kcal · 6 P · 6 F · 6 C", 6, 5.5)
        self.assertClean()

    def test_a_portion_half_rounded_down_fails(self):
        self.meal(["[[Test unit]] = 12100 g"], 121, 121, 12100, portions=22)
        self.day("- [[Half meal]] = 1 portion — 5 kcal · 5 P · 5 F · 5 C", 5, 5.5)
        self.assertError("kcal")

    def test_a_portion_division_that_lands_on_a_half_rounds_up(self):
        """The portions division stays decimal: 69 kcal over 2 portions is 34.5."""
        # 9.2 x 750 / 100 = 69 kcal and 0.7 x 750 / 100 = 5.25 -> 5.3 stored.
        # One of the two portions: 69 / 2 = 34.5 -> 35 kcal, 5.3 / 2 = 2.65 -> 2.7.
        self.meal(["[[Half maker]] = 750 g"], 69, 5.3, 750, portions=2)
        self.day("- [[Half meal]] = 1 portion — 35 kcal · 35 P · 35 F · 35 C", 35, 2.7)
        self.assertClean()


if __name__ == "__main__":
    unittest.main()

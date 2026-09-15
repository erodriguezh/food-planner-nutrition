"""Tests for the strict rounding rule on the vault files (#25, feedback item 2).

One Food whose seven per-100-g values are all 1, so `n` grams give exactly
n / 100 of every total. The Meal built from it puts the stored totals on the
rounding boundary, which is what the lint compares against.

Run: python3 -m unittest discover lint
"""
import unittest

from test_meal_day import LintCase
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


def unit_meal(grams, macro, nutrient, weight=None):
    """A one-ingredient Meal of `grams` of Test unit with the stored totals given."""
    return (
        "---\n"
        "type: meal\n"
        "name: Unit meal\n"
        "ingredients:\n"
        f'  - "[[Test unit]] = {grams} g"\n'
        "portions: 1\n"
        f"weight_g: {grams if weight is None else weight}\n"
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


if __name__ == "__main__":
    unittest.main()

"""Tests for the Meal and Day lint rules (#25).

Run: python3 -m unittest discover lint
"""
import os
import unittest

from test_vault_lint import VaultFixture, INDEX
from vault_lint import lint_vault

# Two Foods with every nutrient, so a Meal can sum fiber, sugar and salt.
SKYR = """---
type: food
name: Skyr
aliases:
  - skyr natur
category: dairy
kcal_per_100g: 64
protein_g_per_100g: 11
fat_g_per_100g: 0.2
carbs_g_per_100g: 4
fiber_g_per_100g: 0
sugar_g_per_100g: 4
salt_g_per_100g: 0.1
servings:
  - "1 portion = 200 g"
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""

RICE = """---
type: food
name: Rice
aliases:
  - Reis
category: grain
kcal_per_100g: 352
protein_g_per_100g: 7.4
fat_g_per_100g: 0.9
carbs_g_per_100g: 78
fiber_g_per_100g: 1
sugar_g_per_100g: 0.2
salt_g_per_100g: 0
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""

# An estimate scaled from Rice: the one Food that carries the estimate mark.
BULGUR = """---
type: food
name: Bulgur
category: grain
kcal_per_100g: 342
protein_g_per_100g: 12.3
fat_g_per_100g: 1.3
carbs_g_per_100g: 75.9
fiber_g_per_100g: 12.5
sugar_g_per_100g: 0.4
salt_g_per_100g: 0
label_basis: 100g
number_source: estimate
estimated_from: "[[Rice]]"
source_date: 2026-09-15
reviewed: false
---
"""

# Skyr 200 g + Rice 100 g: 128 + 352 kcal, 22 + 7.4 P, 0.4 + 0.9 F, 8 + 78 C,
# 0 + 1 fiber, 8 + 0.2 sugar, 0.2 + 0 salt.
BOWL = """---
type: meal
name: Rice bowl
aliases:
  - the bowl
slots:
  - lunch
  - dinner
ingredients:
  - "[[Skyr]] = 200 g"
  - "[[Rice]] = 100 g"
portions: 2
weight_g: 300
kcal: 480
protein_g: 29
fat_g: 1
carbs_g: 86
fiber_g: 1
sugar_g: 8.2
salt_g: 0.2
totals_date: 2026-09-15
estimated: false
reviewed: true
---
"""

FOOD_INDEX = (
    "## Food\n"
    "- [[Skyr]] | dairy | skyr natur\n"
    "- [[Rice]] | grain | Reis\n"
    "- [[Bulgur]] | grain\n"
)
MEAL_INDEX = "## Meal\n- [[Rice bowl]] | lunch, dinner | the bowl\n"
INDEX_WITH_MEAL = INDEX.replace("## Food\n", FOOD_INDEX).replace("## Meal\n", MEAL_INDEX)


class MealFixture(VaultFixture):
    def __init__(self):
        super().__init__()
        self.write("nodes/food/Skyr.md", SKYR)
        self.write("nodes/food/Rice.md", RICE)
        self.write("nodes/food/Bulgur.md", BULGUR)
        self.write("nodes/meal/Rice bowl.md", BOWL)
        self.write("index.md", INDEX_WITH_MEAL)


class LintCase(unittest.TestCase):
    fixture = MealFixture

    def setUp(self):
        self.vault = self.fixture()

    def tearDown(self):
        self.vault.cleanup()

    def errors(self):
        return lint_vault(self.vault.root)

    def assertError(self, needle):
        errors = self.errors()
        self.assertTrue(any(needle in e for e in errors), f"expected an error containing {needle!r}, got {errors}")

    def assertClean(self):
        self.assertEqual(self.errors(), [])


class MealLintTest(LintCase):
    def meal(self, text):
        self.vault.write("nodes/meal/Rice bowl.md", text)

    # --- green path -----------------------------------------------------

    def test_clean_meal_passes(self):
        self.assertClean()

    # --- location and required properties --------------------------------

    def test_meal_outside_the_meal_folder_fails(self):
        os.remove(self.vault.root / "nodes/meal/Rice bowl.md")
        self.vault.write("nodes/food/Rice bowl.md", BOWL)
        self.assertError("nodes/meal/Rice bowl.md")

    def test_meal_in_a_subfolder_fails(self):
        os.remove(self.vault.root / "nodes/meal/Rice bowl.md")
        self.vault.write("nodes/meal/lunch/Rice bowl.md", BOWL)
        self.assertError("nodes/meal/Rice bowl.md")

    def test_meal_missing_required_property_fails(self):
        for key in ("portions", "weight_g", "kcal", "fiber_g", "salt_g", "totals_date", "estimated", "reviewed"):
            with self.subTest(key=key):
                line = next(l for l in BOWL.split("\n") if l.startswith(f"{key}:"))
                self.meal(BOWL.replace(line + "\n", ""))
                self.assertError(key)

    def test_meal_missing_ingredients_fails(self):
        self.meal(BOWL.replace('ingredients:\n  - "[[Skyr]] = 200 g"\n  - "[[Rice]] = 100 g"\n', ""))
        self.assertError("ingredients")

    def test_meal_unknown_property_fails(self):
        self.meal(BOWL.replace("reviewed: true", "reviewed: true\nnumber_source: database"))
        self.assertError("number_source")

    def test_meal_totals_date_must_be_a_date(self):
        self.meal(BOWL.replace("totals_date: 2026-09-15", "totals_date: today"))
        self.assertError("totals_date")

    def test_meal_checkboxes(self):
        self.meal(BOWL.replace("estimated: false", "estimated: no"))
        self.assertError("estimated")
        self.meal(BOWL.replace("reviewed: true", "reviewed: yes"))
        self.assertError("reviewed")

    def test_meal_portions_must_be_a_positive_number(self):
        self.meal(BOWL.replace("portions: 2", "portions: two"))
        self.assertError("portions")
        self.meal(BOWL.replace("portions: 2", "portions: 0"))
        self.assertError("portions")

    def test_meal_cooked_weight_is_optional_and_a_number(self):
        self.meal(BOWL.replace("weight_g: 300", "weight_g: 300\ncooked_weight_g: 260"))
        self.assertClean()
        self.meal(BOWL.replace("weight_g: 300", "weight_g: 300\ncooked_weight_g: some"))
        self.assertError("cooked_weight_g")

    # --- slots ---------------------------------------------------------

    def test_meal_slot_must_be_a_slot_word(self):
        self.meal(BOWL.replace("  - lunch\n", "  - brunch\n"))
        self.assertError("brunch")

    def test_meal_without_slots_means_any(self):
        self.meal(BOWL.replace("slots:\n  - lunch\n  - dinner\n", ""))
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("| lunch, dinner |", "| any |"))
        self.assertClean()

    def test_meal_slots_must_be_a_list(self):
        self.meal(BOWL.replace("slots:\n  - lunch\n  - dinner\n", "slots: lunch\n"))
        self.assertError("slots")

    # --- ingredients -------------------------------------------------------

    def test_ingredient_shape(self):
        for bad in ('"[[Skyr]] 200 g"', '"[[Skyr]] = 200"', '"[[Skyr]] = 1 portion"', '"Skyr = 200 g"', '"[[Skyr]] = 200 ml"'):
            with self.subTest(bad=bad):
                self.meal(BOWL.replace('"[[Skyr]] = 200 g"', bad))
                self.assertError("ingredients")

    def test_ingredient_must_link_an_existing_food(self):
        self.meal(BOWL.replace('"[[Skyr]] = 200 g"', '"[[Quark]] = 200 g"'))
        self.assertError("Quark")

    def test_ingredient_must_not_be_a_meal(self):
        other = BOWL.replace("name: Rice bowl", "name: Side").replace("aliases:\n  - the bowl\n", "")
        self.vault.write("nodes/meal/Side.md", other)
        self.meal(BOWL.replace('"[[Rice]] = 100 g"', '"[[Side]] = 100 g"'))
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("## Meal\n", "## Meal\n- [[Side]] | lunch, dinner\n"))
        self.assertError("Side")

    def test_one_item_per_food(self):
        self.meal(BOWL.replace('"[[Rice]] = 100 g"', '"[[Rice]] = 50 g"\n  - "[[Rice]] = 50 g"'))
        self.assertError("Rice")

    def test_empty_ingredient_list_fails(self):
        self.meal(BOWL.replace('  - "[[Skyr]] = 200 g"\n  - "[[Rice]] = 100 g"\n', ""))
        self.assertError("ingredients")

    def test_ingredient_food_needs_fiber_sugar_and_salt(self):
        """Spec #22: a missing nutrient is filled and written to the Food, so a
        Meal never sums a gap as zero."""
        self.vault.write("nodes/food/Skyr.md", SKYR.replace("fiber_g_per_100g: 0\n", ""))
        self.assertError("fiber_g_per_100g")

    # --- weight and totals from the Food nodes -----------------------------

    def test_weight_must_equal_the_ingredient_sum(self):
        self.meal(BOWL.replace("weight_g: 300", "weight_g: 310"))
        self.assertError("weight_g")

    def test_totals_must_match_the_food_nodes(self):
        self.meal(BOWL.replace("kcal: 480", "kcal: 500"))
        self.assertError("kcal")
        self.meal(BOWL.replace("protein_g: 29", "protein_g: 30"))
        self.assertError("protein_g")
        self.meal(BOWL.replace("sugar_g: 8.2", "sugar_g: 8.5"))
        self.assertError("sugar_g")

    def test_totals_within_the_rounding_pass(self):
        # Fat is 1.3 exactly; the rule stores 1, and a value inside half a unit also passes.
        self.meal(BOWL.replace("fat_g: 1", "fat_g: 1.3"))
        self.assertClean()

    def test_a_changed_food_makes_the_stored_totals_stale(self):
        """Story 32: totals are recomputed when an ingredient Food changed. The
        lint catches the stale Meal so the agent recomputes."""
        self.vault.write("nodes/food/Rice.md", RICE.replace("kcal_per_100g: 352", "kcal_per_100g: 360"))
        self.assertError("kcal")

    # --- the estimate mark -----------------------------------------------

    def test_estimated_must_be_true_when_an_ingredient_is_an_estimate(self):
        self.meal(BOWL.replace('"[[Rice]] = 100 g"', '"[[Bulgur]] = 100 g"').replace("kcal: 480", "kcal: 470")
                  .replace("protein_g: 29", "protein_g: 34").replace("fat_g: 1", "fat_g: 2").replace("carbs_g: 86", "carbs_g: 84")
                  .replace("fiber_g: 1", "fiber_g: 12.5").replace("sugar_g: 8.2", "sugar_g: 8.4"))
        self.assertError("estimated")

    def test_estimated_must_be_false_when_no_ingredient_is_an_estimate(self):
        self.meal(BOWL.replace("estimated: false", "estimated: true"))
        self.assertError("estimated")

    def test_estimated_meal_with_an_estimate_ingredient_passes(self):
        self.meal(BOWL.replace('"[[Rice]] = 100 g"', '"[[Bulgur]] = 100 g"').replace("kcal: 480", "kcal: 470")
                  .replace("protein_g: 29", "protein_g: 34").replace("fat_g: 1", "fat_g: 2").replace("carbs_g: 86", "carbs_g: 84")
                  .replace("fiber_g: 1", "fiber_g: 12.5").replace("sugar_g: 8.2", "sugar_g: 8.4")
                  .replace("estimated: false", "estimated: true"))
        self.assertClean()

    # --- body ------------------------------------------------------------

    def test_meal_body_allows_prepare_and_notes_only(self):
        self.meal(BOWL + "\n## Prepare\n\nCook the rice.\n\n## Notes\n\nGood cold.\n")
        self.assertClean()
        self.meal(BOWL + "\n## Notes\n\nGood cold.\n")
        self.assertClean()
        self.meal(BOWL + "\n## Steps\n\nCook.\n")
        self.assertError("Prepare")

    def test_meal_body_sections_keep_their_order(self):
        self.meal(BOWL + "\n## Notes\n\nGood.\n\n## Prepare\n\nCook.\n")
        self.assertError("Prepare")

    def test_meal_body_free_prose_fails(self):
        self.meal(BOWL + "\nCook the rice first.\n")
        self.assertError("Prepare")

    # --- Index Meal line ---------------------------------------------------

    def test_meal_index_line_slots_must_match(self):
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("| lunch, dinner |", "| lunch |"))
        self.assertError("Rice bowl")

    def test_meal_index_line_needs_the_slot_field(self):
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("- [[Rice bowl]] | lunch, dinner | the bowl\n", "- [[Rice bowl]]\n"))
        self.assertError("Rice bowl")

    def test_meal_index_line_must_list_all_aliases(self):
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("| the bowl\n", "\n"))
        self.assertError("the bowl")

    def test_meal_index_line_must_not_invent_aliases(self):
        self.vault.write("index.md", INDEX_WITH_MEAL.replace("| the bowl\n", "| the bowl, bowl\n"))
        self.assertError("bowl")

    def test_meal_without_index_line_fails(self):
        self.vault.write("index.md", INDEX_WITH_MEAL.replace(MEAL_INDEX, "## Meal\n"))
        self.assertError("Rice bowl")


if __name__ == "__main__":
    unittest.main()

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

    def test_an_unrounded_total_fails(self):
        # Fat is 1.3 exactly; the rule stores 1, and the exact value is not stored.
        self.meal(BOWL.replace("fat_g: 1", "fat_g: 1.3"))
        self.assertError("fat_g")

    def test_a_newer_ingredient_food_makes_the_meal_stale(self):
        """Story 32 and feedback item 4: an ingredient Food changed after the
        Meal's totals_date, and the numbers moved with it."""
        self.vault.write("nodes/food/Rice.md", RICE.replace("kcal_per_100g: 352", "kcal_per_100g: 360")
                         .replace("source_date: 2026-09-15", "source_date: 2026-09-16"))
        self.assertError("stale")

    def test_a_source_date_bump_alone_makes_the_meal_stale(self):
        """Feedback item 4: the Food was re-sourced and its numbers happen to be
        the same, so the totals still match. The Meal is stale all the same."""
        self.vault.write("nodes/food/Rice.md", RICE.replace("source_date: 2026-09-15", "source_date: 2026-09-16"))
        self.assertError("stale")

    def test_a_meal_recomputed_after_the_food_is_not_stale(self):
        self.vault.write("nodes/food/Rice.md", RICE.replace("source_date: 2026-09-15", "source_date: 2026-09-16"))
        self.meal(BOWL.replace("totals_date: 2026-09-15", "totals_date: 2026-09-16"))
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

# Rice bowl by portion: stored totals / 2 -> 240 kcal, 14.5 -> 15 P, 0.5 -> 1 F, 43 C.
# Rice 150 g: 528 kcal, 11.1 -> 11 P, 1.35 -> 1 F, 117 C.
# Bulgur 50 g (an estimate): 171 kcal, 6.15 -> 6 P, 0.65 -> 1 F, 37.95 -> 38 C.
# Rice bowl, one of two portions, with 300 g Skyr on the plate instead of the listed 100 g per
# portion: 240 - 64 + 192 = 368 kcal, 14.5 - 11 + 33 = 36.5 -> 37 P, 0.5 - 0.2 + 0.6 = 0.9 -> 1 F,
# 43 - 4 + 12 = 51 C.
DAY = """---
type: day
name: 2026-09-15
date: 2026-09-15
status: open
goal: "[[Goals]]"
kcal: 1307
protein_g: 69
fat_g: 4
carbs_g: 249
fiber_g: 8.8
sugar_g: 16.7
salt_g: 0.4
estimated: true
---

## Breakfast

- [[Rice bowl]] = 1 portion — 240 kcal · 15 P · 1 F · 43 C

## Lunch

- [[Rice]] = 150 g — 528 kcal · 11 P · 1 F · 117 C

## Snack

- ~ [[Bulgur]] = 50 g — 171 kcal · 6 P · 1 F · 38 C

## Dinner

- [[Rice bowl]] = 1 portion, [[Skyr]] = 300 g — 368 kcal · 37 P · 1 F · 51 C
"""

BREAKFAST = "- [[Rice bowl]] = 1 portion — 240 kcal · 15 P · 1 F · 43 C"
LUNCH = "- [[Rice]] = 150 g — 528 kcal · 11 P · 1 F · 117 C"
SNACK = "- ~ [[Bulgur]] = 50 g — 171 kcal · 6 P · 1 F · 38 C"
DINNER = "- [[Rice bowl]] = 1 portion, [[Skyr]] = 300 g — 368 kcal · 37 P · 1 F · 51 C"

DAY_INDEX = INDEX_WITH_MEAL.replace("## Day\n", "## Day\n- 2026-09 | nodes/day/2026-09/\n")
OPEN_STATE = """---
type: state
open_day: "[[2026-09-15]]"
updated: 2026-09-15
---

## Open items
"""


class DayFixture(MealFixture):
    def __init__(self):
        super().__init__()
        self.write("nodes/day/2026-09/2026-09-15.md", DAY)
        self.write("index.md", DAY_INDEX)
        self.write("state.md", OPEN_STATE)


class DayLintTest(LintCase):
    fixture = DayFixture

    def day(self, text):
        self.vault.write("nodes/day/2026-09/2026-09-15.md", text)

    def closed(self, text=DAY):
        """The same Day, closed, with the State cleared."""
        self.day(text.replace("status: open", "status: closed"))
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))

    # --- green path -----------------------------------------------------

    def test_clean_day_passes(self):
        self.assertClean()

    # --- location, name and date -----------------------------------------

    def test_day_outside_its_month_folder_fails(self):
        os.remove(self.vault.root / "nodes/day/2026-09/2026-09-15.md")
        self.vault.write("nodes/day/2026-10/2026-09-15.md", DAY)
        self.vault.write("index.md", DAY_INDEX.replace("- 2026-09 | nodes/day/2026-09/", "- 2026-10 | nodes/day/2026-10/"))
        self.assertError("nodes/day/2026-09/2026-09-15.md")

    def test_day_directly_under_the_day_folder_fails(self):
        os.remove(self.vault.root / "nodes/day/2026-09/2026-09-15.md")
        self.vault.write("nodes/day/2026-09-15.md", DAY)
        self.assertError("nodes/day/2026-09/2026-09-15.md")

    def test_day_name_must_equal_the_date(self):
        self.day(DAY.replace("date: 2026-09-15", "date: 2026-09-14"))
        self.assertError("date")

    def test_day_date_must_be_a_date(self):
        self.day(DAY.replace("name: 2026-09-15\ndate: 2026-09-15", "name: 2026-09-15\ndate: Monday"))
        self.assertError("date")

    # --- frontmatter -------------------------------------------------------

    def test_day_missing_required_property_fails(self):
        for key in ("status", "goal", "kcal", "salt_g", "estimated"):
            with self.subTest(key=key):
                line = next(l for l in DAY.split("\n") if l.startswith(f"{key}:"))
                self.day(DAY.replace(line + "\n", ""))
                self.assertError(key)

    def test_day_unknown_property_fails(self):
        self.day(DAY.replace("estimated: true", "estimated: true\nweight_kg: 80"))
        self.assertError("weight_kg")

    def test_day_status_enum(self):
        self.day(DAY.replace("status: open", "status: done"))
        self.assertError("status")

    def test_day_goal_is_the_goals_link(self):
        self.day(DAY.replace('goal: "[[Goals]]"', 'goal: "[[Pantry]]"'))
        self.assertError("goal")
        self.day(DAY.replace('goal: "[[Goals]]"', "goal: Goals"))
        self.assertError("goal")

    def test_day_totals_must_be_numbers(self):
        self.day(DAY.replace("kcal: 1307", "kcal: lots"))
        self.assertError("kcal")

    def test_day_estimated_is_a_checkbox(self):
        self.day(DAY.replace("estimated: true", "estimated: yes"))
        self.assertError("estimated")

    # --- body shape --------------------------------------------------------

    def test_slot_sections_keep_the_fixed_order(self):
        self.day(DAY.replace(f"## Breakfast\n\n{BREAKFAST}\n\n## Lunch\n\n{LUNCH}\n", f"## Lunch\n\n{LUNCH}\n\n## Breakfast\n\n{BREAKFAST}\n"))
        self.assertError("order")

    def test_only_present_slots_are_written_and_an_empty_slot_fails(self):
        self.day(DAY.replace(f"## Snack\n\n{SNACK}\n\n", "## Snack\n\n"))
        self.assertError("Snack")

    def test_a_slot_section_twice_fails(self):
        self.day(DAY + f"\n## Dinner\n\n{DINNER}\n")
        self.assertError("second")

    def test_other_heading_fails(self):
        self.day(DAY + "\n## Plan\n\nLunch: rice.\n")
        self.assertError("Plan")

    def test_text_before_the_first_heading_fails(self):
        self.day(DAY.replace("---\n\n## Breakfast", "---\n\nA good day.\n\n## Breakfast"))
        self.assertError("A good day.")

    def test_summary_and_notes_are_allowed_after_the_slots(self):
        self.closed(DAY + "\n## Summary\n\nTable here.\n\n## Notes\n\nFelt fine.\n")
        self.assertClean()

    def test_notes_before_summary_fails(self):
        self.closed(DAY + "\n## Notes\n\nFelt fine.\n\n## Summary\n\nTable here.\n")
        self.assertError("order")

    def test_a_slot_section_holds_entry_lines_only(self):
        self.day(DAY.replace(f"{LUNCH}\n", f"{LUNCH}\nat the office\n"))
        self.assertError("entry line")

    # --- entry line shape ----------------------------------------------------

    def test_entry_line_needs_the_dash_and_the_four_macros(self):
        self.day(DAY.replace(LUNCH, "- [[Rice]] = 150 g: 528 kcal · 11 P · 1 F · 117 C"))
        self.assertError("entry line")
        self.day(DAY.replace(LUNCH, "- [[Rice]] = 150 g — 528 kcal · 11 P · 1 F"))
        self.assertError("entry line")

    def test_the_mark_sits_right_after_the_bullet_only(self):
        self.day(DAY.replace(SNACK, "- [[Bulgur]] ~ = 50 g — 171 kcal · 6 P · 1 F · 38 C"))
        self.assertError("entry line")
        self.day(DAY.replace(SNACK, "- ~[[Bulgur]] = 50 g — 171 kcal · 6 P · 1 F · 38 C"))
        self.assertError("entry line")
        self.day(DAY.replace(SNACK, "- *[[Bulgur]] = 50 g* — 171 kcal · 6 P · 1 F · 38 C"))
        self.assertError("entry line")

    def test_no_time_and_no_checkbox_on_the_line(self):
        self.day(DAY.replace(LUNCH, "- [ ] " + LUNCH[2:]))
        self.assertError("entry line")
        self.day(DAY.replace(LUNCH, LUNCH.replace("= 150 g", "= 150 g at 12:40")))
        self.assertError("entry line")

    def test_entry_must_link_a_food_or_meal(self):
        self.day(DAY.replace("[[Rice]] = 150 g", "[[Quark]] = 150 g"))
        self.assertError("Quark")
        self.day(DAY.replace("[[Rice]] = 150 g", "[[Goals]] = 150 g"))
        self.assertError("Goals")

    def test_a_food_is_logged_in_grams_only(self):
        self.day(DAY.replace("[[Rice]] = 150 g", "[[Rice]] = 1 portion"))
        self.assertError("portion")

    def test_a_meal_by_grams_passes(self):
        # 150 g of a 300 g Meal is half: the same numbers as one of two portions.
        self.day(DAY.replace("[[Rice bowl]] = 1 portion —", "[[Rice bowl]] = 150 g —"))
        self.assertClean()

    # --- the ingredient change ---------------------------------------------------

    def test_ingredient_change_needs_a_meal(self):
        self.day(DAY.replace(LUNCH, "- [[Rice]] = 150 g, [[Skyr]] = 100 g — 528 kcal · 11 P · 1 F · 117 C"))
        self.assertError("ingredient change")

    def test_ingredient_change_names_an_ingredient_of_the_meal(self):
        self.day(DAY.replace("[[Skyr]] = 300 g", "[[Bulgur]] = 300 g"))
        self.assertError("Bulgur")

    def test_ingredient_change_needs_a_portion_amount(self):
        self.day(DAY.replace("[[Rice bowl]] = 1 portion, [[Skyr]]", "[[Rice bowl]] = 150 g, [[Skyr]]"))
        self.assertError("portion")

    # --- the estimate mark ---------------------------------------------------------

    def test_an_estimated_food_needs_the_mark(self):
        self.day(DAY.replace(SNACK, SNACK.replace("- ~ ", "- ")))
        self.assertError("~")

    def test_an_estimated_meal_needs_the_mark(self):
        bowl = BOWL.replace('"[[Rice]] = 100 g"', '"[[Bulgur]] = 100 g"').replace("kcal: 480", "kcal: 470") \
            .replace("protein_g: 29", "protein_g: 34").replace("fat_g: 1", "fat_g: 2").replace("carbs_g: 86", "carbs_g: 84") \
            .replace("fiber_g: 1", "fiber_g: 12.5").replace("sugar_g: 8.2", "sugar_g: 8.4").replace("estimated: false", "estimated: true")
        self.vault.write("nodes/meal/Rice bowl.md", bowl)
        self.day(DAY.replace(BREAKFAST, "- [[Rice bowl]] = 1 portion — 235 kcal · 17 P · 1 F · 42 C"))
        self.assertError("~")

    def test_a_guessed_amount_may_carry_the_mark_on_a_plain_food(self):
        self.day(DAY.replace(LUNCH, "- ~ " + LUNCH[2:]))
        self.assertClean()

    def test_day_estimated_false_with_a_marked_line_fails(self):
        self.day(DAY.replace("estimated: true", "estimated: false"))
        self.assertError("estimated")

    def test_day_estimated_true_without_a_marked_line_fails(self):
        # Replace the estimated Bulgur line with a plain Rice line of the same numbers.
        plain = DAY.replace(SNACK, "- [[Rice]] = 50 g — 176 kcal · 4 P · 0 F · 39 C").replace("kcal: 1307", "kcal: 1312") \
            .replace("protein_g: 69", "protein_g: 67").replace("fat_g: 4", "fat_g: 3").replace("carbs_g: 249", "carbs_g: 250") \
            .replace("fiber_g: 8.8", "fiber_g: 3").replace("sugar_g: 16.7", "sugar_g: 16.6")
        self.day(plain)
        self.assertError("estimated")
        self.day(plain.replace("estimated: true", "estimated: false"))
        self.assertClean()

    # --- totals from the lines ------------------------------------------------------

    def test_totals_must_equal_the_sum_of_the_lines(self):
        self.day(DAY.replace("kcal: 1307", "kcal: 1300"))
        self.assertError("kcal")
        self.day(DAY.replace("protein_g: 69", "protein_g: 70"))
        self.assertError("protein_g")

    def test_a_closed_day_keeps_its_totals_when_a_food_changes(self):
        """Spec #22: a reformulated product overwrites the Food; closed Days keep their totals."""
        self.closed()
        self.vault.write("nodes/food/Rice.md", RICE.replace("kcal_per_100g: 352", "kcal_per_100g: 360"))
        self.vault.write("nodes/meal/Rice bowl.md", BOWL.replace("kcal: 480", "kcal: 488"))
        self.assertClean()

    def test_an_open_day_line_must_match_its_node(self):
        self.day(DAY.replace(LUNCH, "- [[Rice]] = 150 g — 540 kcal · 11 P · 1 F · 117 C").replace("kcal: 1307", "kcal: 1319"))
        self.assertError("540")

    def test_an_open_day_nutrient_totals_come_from_the_nodes(self):
        self.day(DAY.replace("sugar_g: 16.7", "sugar_g: 20"))
        self.assertError("sugar_g")

    def test_a_closed_day_total_still_must_equal_its_lines(self):
        self.closed(DAY.replace("kcal: 1307", "kcal: 1300"))
        self.assertError("kcal")

    # --- State and Index -----------------------------------------------------------

    def test_state_must_point_to_the_open_day(self):
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))
        self.assertError("open_day")

    def test_two_open_days_fail(self):
        second = DAY.replace("2026-09-15", "2026-09-16")
        self.vault.write("nodes/day/2026-09/2026-09-16.md", second)
        self.assertError("open")

    def test_an_auto_closed_day_and_one_open_day_pass(self):
        older = DAY.replace("2026-09-15", "2026-09-14").replace("status: open", "status: auto-closed")
        self.vault.write("nodes/day/2026-09/2026-09-14.md", older)
        self.assertClean()

    def test_every_day_folder_needs_its_month_line(self):
        self.vault.write("index.md", INDEX_WITH_MEAL)
        self.assertError("2026-09")

    def test_a_second_month_line_fails(self):
        self.vault.write("index.md", DAY_INDEX.replace("## Day\n", "## Day\n- 2026-09 | nodes/day/2026-09/\n"))
        self.assertError("2026-09")


if __name__ == "__main__":
    unittest.main()

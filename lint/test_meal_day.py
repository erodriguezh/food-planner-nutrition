"""Tests for the Meal and Day lint rules (#25).

Run: python3 -m unittest discover lint
"""
import os
import unittest

from test_vault_lint import VaultFixture, GOALS, INDEX
from vault_lint import SUMMARY_SEPARATOR, lint_vault

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

# The same Day with the estimated Bulgur snack replaced by a plain Rice line of
# the same amount, so no line carries the mark: Rice 50 g is 176 kcal, 3.7 -> 4 P,
# 0.45 -> 0 F, 39 C.
PLAIN_DAY = DAY.replace(SNACK, "- [[Rice]] = 50 g — 176 kcal · 4 P · 0 F · 39 C") \
    .replace("kcal: 1307", "kcal: 1312").replace("protein_g: 69", "protein_g: 67") \
    .replace("fat_g: 4", "fat_g: 3").replace("carbs_g: 249", "carbs_g: 250") \
    .replace("fiber_g: 8.8", "fiber_g: 3").replace("sugar_g: 16.7", "sugar_g: 16.6")

# The Summary a closed Day carries (#26): the slot table with its TOTAL row, the
# goal line, one bullet per macro against its target, the verdict in the fixed
# words of spec #22 and an optional hint. DAY is estimated, so every table
# number carries the `~`.
SUMMARY = """
## Summary

| slot | kcal | P | F | C |
| --- | --- | --- | --- | --- |
| breakfast | ~240 | ~15 | ~1 | ~43 |
| lunch | ~528 | ~11 | ~1 | ~117 |
| snack | ~171 | ~6 | ~1 | ~38 |
| dinner | ~368 | ~37 | ~1 | ~51 |
| TOTAL | ~1307 | ~69 | ~4 | ~249 |

Goal 2500 kcal (2375-2625), 135 P (128-142), 60 F (57-63), 355 C (337-373).

- kcal 1193 under
- protein 66 under
- fat 56 under
- carbs 106 under

off target: kcal low, protein low, fat low, carbs low

Hint: more protein at lunch.
"""

# The Goals snapshot the close stores in the Summary (#26, PR #32 review round
# 2, item 2): every target with the range it was judged against. The refresh
# reads the line back instead of today's Goals.
GOAL_LINE = "Goal 2500 kcal (2375-2625), 135 P (128-142), 60 F (57-63), 355 C (337-373)."

# The same Day closed under a Goals node whose targets are the day itself, so
# every macro sits inside its stored range and the verdict reads `on target`.
ON_TARGET_GOAL_LINE = "Goal 1307 kcal (1242-1372), 69 P (66-72), 4 F (4-4), 249 C (237-261)."
ON_TARGET = SUMMARY.replace(GOAL_LINE, ON_TARGET_GOAL_LINE) \
    .replace("- kcal 1193 under", "- kcal 0 under").replace("- protein 66 under", "- protein 0 under") \
    .replace("- fat 56 under", "- fat 0 under").replace("- carbs 106 under", "- carbs 0 under") \
    .replace("off target: kcal low, protein low, fat low, carbs low", "on target")

# The same Day closed under Goals that put two of its four macros outside their
# range: the verdict then names two distinct macros, in the column order of the
# bullets (PR #32 review round 2, item 4).
TWO_OFF = ON_TARGET.replace(ON_TARGET_GOAL_LINE,
                            "Goal 1400 kcal (1330-1470), 69 P (66-72), 10 F (9-11), 249 C (237-261).") \
    .replace("- kcal 0 under", "- kcal 93 under").replace("- fat 0 under", "- fat 6 under") \
    .replace("on target", "off target: kcal low, fat low")

# Today's Goals, changed after the Day was closed: the node the refresh must not
# read for an old Day. Bounds are the target plus or minus 5 %, half up.
GOALS_B = GOALS.replace("kcal: 2500", "kcal: 1300").replace("protein_g: 135", "protein_g: 70") \
    .replace("fat_g: 60", "fat_g: 4").replace("carbs_g: 355", "carbs_g: 250") \
    .replace("kcal_min: 2375", "kcal_min: 1235").replace("kcal_max: 2625", "kcal_max: 1365") \
    .replace("protein_g_min: 128", "protein_g_min: 67").replace("protein_g_max: 142", "protein_g_max: 74") \
    .replace("fat_g_min: 57", "fat_g_min: 4").replace("fat_g_max: 63", "fat_g_max: 4") \
    .replace("carbs_g_min: 337", "carbs_g_min: 238").replace("carbs_g_max: 373", "carbs_g_max: 263") \
    .replace("since: 2026-09-15", "since: 2026-09-16")

# The Summary of PLAIN_DAY: no line is marked, so no `~` anywhere.
PLAIN_SUMMARY = SUMMARY.replace("~", "") \
    .replace("| snack | 171 | 6 | 1 | 38 |", "| snack | 176 | 4 | 0 | 39 |") \
    .replace("| TOTAL | 1307 | 69 | 4 | 249 |", "| TOTAL | 1312 | 67 | 3 | 250 |") \
    .replace("kcal 1193 under", "kcal 1188 under").replace("protein 66 under", "protein 68 under") \
    .replace("fat 56 under", "fat 57 under").replace("carbs 106 under", "carbs 105 under")

# The Day after the one correction three tests log into a closed Day (#26): the
# lunch entry drops from 150 g to 100 g of Rice, so the Day totals follow it,
# the four macros and the nutrients the smaller entry carries as well.
SMALLER_LUNCH = "- [[Rice]] = 100 g — 352 kcal · 7 P · 1 F · 78 C"
CORRECTED_DAY = DAY.replace(LUNCH, SMALLER_LUNCH) \
    .replace("kcal: 1307", "kcal: 1131").replace("protein_g: 69", "protein_g: 65") \
    .replace("carbs_g: 249", "carbs_g: 210") \
    .replace("fiber_g: 8.8", "fiber_g: 8.3").replace("sugar_g: 16.7", "sugar_g: 16.6")


def corrected_table(summary):
    """The slot table of `summary` rewritten for `CORRECTED_DAY`: the lunch row
    and the TOTAL row follow the smaller entry. The bullets and the verdict come
    from the goal line the Summary carries, so each test writes its own."""
    return summary.replace("| lunch | ~528 | ~11 | ~1 | ~117 |", "| lunch | ~352 | ~7 | ~1 | ~78 |") \
        .replace("| TOTAL | ~1307 | ~69 | ~4 | ~249 |", "| TOTAL | ~1131 | ~65 | ~4 | ~210 |")


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

    def closed(self, text=DAY, status="closed"):
        """The same Day, closed or auto-closed, with its Summary and the State cleared.

        A Day without a Summary gets the one that fits its `estimated` value.
        """
        if "## Summary" not in text:
            text += SUMMARY if "estimated: true" in text else PLAIN_SUMMARY
        self.day(text.replace("status: open", f"status: {status}"))
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))

    def rice_becomes_an_estimate(self):
        """The owner's example: Rice is re-sourced as `number_source: estimate` after
        the Day was written, and the Meal that holds it is recomputed. Its numbers do
        not change, so `source_date` and `totals_date` still agree and the Meal is not
        stale; only its `estimated` turns true.
        """
        self.vault.write("nodes/food/Rice.md", RICE.replace(
            "number_source: database", 'number_source: estimate\nestimated_from: "[[Bulgur]]"'))
        self.vault.write("nodes/meal/Rice bowl.md", BOWL.replace("estimated: false", "estimated: true"))

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
        self.closed(DAY + SUMMARY + "\n## Notes\n\nFelt fine.\n")
        self.assertClean()

    def test_notes_before_summary_fails(self):
        self.closed(DAY + "\n## Notes\n\nFelt fine.\n" + SUMMARY)
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
        """The primary link is checked on every Day. PR #31 review: history freezes
        the numbers the line recorded, not the canonical shape of the line, so a
        closed and an auto-closed Day fail a link to a node that is neither a
        Food nor a Meal in the same way an open Day does.
        """
        missing = DAY.replace("[[Rice]] = 150 g", "[[Quark]] = 150 g")
        other = DAY.replace("[[Rice]] = 150 g", "[[Goals]] = 150 g")
        self.day(missing)
        self.assertError("Quark")
        self.day(other)
        self.assertError("Goals")
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(missing, status=status)
                self.assertError("Quark")
                self.closed(other, status=status)
                self.assertError("Goals")

    def test_a_food_is_logged_in_grams_only(self):
        self.day(DAY.replace("[[Rice]] = 150 g", "[[Rice]] = 1 portion"))
        self.assertError("portion")

    def test_a_meal_by_grams_passes(self):
        # 150 g of a 300 g Meal is half: the same numbers as one of two portions.
        self.day(DAY.replace("[[Rice bowl]] = 1 portion —", "[[Rice bowl]] = 150 g —"))
        self.assertClean()

    def test_a_guessed_cooked_amount_of_a_meal_carries_the_mark(self):
        """Feedback item 5: a leftover logged in cooked grams converts through the
        Meal's `cooked_weight_g` before the line is written. Without a cooked
        weight the shrink is a guess, so the grams are an estimated input and the
        line carries the mark, on a Meal that is not itself an estimate."""
        # The Meal stores no cooked weight, so the shrink is a guess: 130 cooked
        # g are about 150 canonical g, a number the agent cannot make exact. The
        # mark is what says so, and the lint sees only the written line.
        marked = "- ~ [[Rice bowl]] = 150 g — 240 kcal · 15 P · 1 F · 43 C"
        text = DAY.replace(BREAKFAST, marked)
        self.assertIn(marked, text)
        self.day(text)
        self.assertClean()

    def test_a_meal_with_a_cooked_weight_is_logged_in_canonical_grams(self):
        """Feedback item 5: the Meal stores the cooked weight once; 130 cooked g
        of a Meal that weighs 300 g raw and 260 g cooked are 150 canonical g. The
        conversion happens before the write, so the line carries 150 g. The same
        macros against the unconverted 130 g are what the lint catches: 130 g of
        the Meal is 208 kcal, not the 240 kcal of half of it."""
        cooked_g, cooked_weight_g, weight_g = 130.0, 260.0, 300.0
        self.assertEqual(cooked_g * weight_g / cooked_weight_g, 150.0)
        self.vault.write("nodes/meal/Rice bowl.md", BOWL.replace("weight_g: 300", "weight_g: 300\ncooked_weight_g: 260"))
        converted = DAY.replace("[[Rice bowl]] = 1 portion —", "[[Rice bowl]] = 150 g —")
        self.assertIn("- [[Rice bowl]] = 150 g —", converted)
        self.day(converted)
        self.assertClean()
        self.day(converted.replace("[[Rice bowl]] = 150 g —", "[[Rice bowl]] = 130 g —"))
        self.assertError("208")

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
        self.day(PLAIN_DAY)
        self.assertError("estimated")
        self.day(PLAIN_DAY.replace("estimated: true", "estimated: false"))
        self.assertClean()

    def test_a_closed_day_keeps_its_marks_when_a_food_becomes_an_estimate(self):
        """PR #31 review: the `~` of a closed Day is history. A Food that turns into an
        estimate after the Day was written leaves the old unmarked line alone.
        """
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(status=status)
                self.rice_becomes_an_estimate()
                self.assertClean()

    def test_an_open_day_still_needs_the_mark_when_a_food_becomes_an_estimate(self):
        """The mirror of the two above: current-node provenance belongs to an open Day."""
        self.rice_becomes_an_estimate()
        self.assertError("[[Rice bowl]] is an estimated Meal, so the line needs the `~` mark")
        self.day(DAY.replace(BREAKFAST, "- ~ " + BREAKFAST[2:]))
        self.assertError("[[Rice]] is an estimated Food, so the line needs the `~` mark")

    def test_a_closed_day_keeps_its_lines_when_a_meal_loses_the_changed_ingredient(self):
        """The same rule for the shape: after the Day was closed, the Meal drops
        the ingredient the dinner line changes. The old line stands; the open
        Day would fail it.
        """
        bowl = BOWL.replace('  - "[[Skyr]] = 200 g"\n', "").replace("weight_g: 300", "weight_g: 100") \
            .replace("kcal: 480", "kcal: 352").replace("protein_g: 29", "protein_g: 7") \
            .replace("carbs_g: 86", "carbs_g: 78").replace("sugar_g: 8.2", "sugar_g: 0.2").replace("salt_g: 0.2", "salt_g: 0")
        self.closed()
        self.vault.write("nodes/meal/Rice bowl.md", bowl)
        self.assertClean()
        self.day(DAY.replace(BREAKFAST, "- [[Rice]] = 50 g — 176 kcal · 4 P · 0 F · 39 C"))
        self.assertError("ingredient change names [[Skyr]], which is not an ingredient of [[Rice bowl]]")

    def test_a_closed_day_estimated_must_still_match_its_lines(self):
        """The invariant that stays on a closed Day: `estimated` is true exactly when a
        line carries the mark, whatever the nodes say today.
        """
        self.closed(DAY.replace("estimated: true", "estimated: false") + SUMMARY.replace("~", ""))
        self.assertError("estimated")
        plain = PLAIN_DAY + SUMMARY
        self.closed(plain)
        self.assertError("estimated")
        self.closed(plain.replace("estimated: true", "estimated: false").replace(SUMMARY, PLAIN_SUMMARY))
        self.assertClean()

    # --- the shape rules every Day keeps --------------------------------------------

    # PR #31 review: history freezes the line's nutrition, its `~` and the Meal
    # it was written against. It never makes a malformed entry line valid, so
    # the canonical shape of #25 is checked on a closed and auto-closed Day too.

    def test_a_closed_day_still_fails_a_food_logged_by_portion(self):
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(DAY.replace("[[Rice]] = 150 g", "[[Rice]] = 1 portion"), status=status)
                self.assertError("is a Food and is logged in grams")

    def test_a_closed_day_still_fails_an_ingredient_change_on_a_food(self):
        changed = "- [[Rice]] = 150 g, [[Skyr]] = 100 g — 528 kcal · 11 P · 1 F · 117 C"
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(DAY.replace(LUNCH, changed), status=status)
                self.assertError("an ingredient change needs a Meal")

    def test_a_closed_day_still_fails_an_ingredient_change_on_a_meal_by_grams(self):
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(DAY.replace("[[Rice bowl]] = 1 portion, [[Skyr]]", "[[Rice bowl]] = 150 g, [[Skyr]]"), status=status)
                self.assertError("an ingredient change is logged by portion")

    def test_the_changed_food_link_must_resolve_to_a_food(self):
        """The changed link is a Food link on every Day: a missing node and a node of
        another type both fail, open or closed. What history frees is whether the
        Meal still lists that Food, not whether the Food exists. Decided with #26
        after the PR #31 review; the rationale sits in test_spec_meal_day.py.
        """
        missing = DAY.replace("[[Skyr]] = 300 g", "[[Quark]] = 300 g")
        other = DAY.replace("[[Skyr]] = 300 g", "[[Goals]] = 300 g")
        self.day(missing)
        self.assertError("names [[Quark]], which does not exist")
        self.day(other)
        self.assertError("names [[Goals]], a goals node, not a Food")
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(missing, status=status)
                self.assertError("names [[Quark]], which does not exist")
                self.closed(other, status=status)
                self.assertError("names [[Goals]], a goals node, not a Food")

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

    # --- the Summary lifecycle (spec #22, feedback item 6) --------------------------

    def test_an_open_day_must_not_have_a_summary(self):
        self.day(DAY + SUMMARY)
        self.assertError("Summary")

    def test_a_closed_day_needs_a_summary(self):
        self.closed(DAY)
        self.assertClean()
        self.day(DAY.replace("status: open", "status: closed"))
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))
        self.assertError("Summary")

    def test_an_auto_closed_day_needs_a_summary(self):
        self.day(DAY.replace("status: open", "status: auto-closed"))
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))
        self.assertError("Summary")

    def test_a_summary_without_the_verdict_words_fails(self):
        """Acceptance #26: a free-text verdict fails."""
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low", "A good day, a bit low."))
        self.assertError("verdict")

    def test_a_free_text_summary_fails(self):
        self.closed(DAY + "\n## Summary\n\nA good day, 1307 kcal.\n")
        self.assertError("TOTAL")

    def test_a_verdict_names_exactly_the_macros_outside_the_stored_bounds(self):
        """PR #32 review round 2, item 2: the Summary carries the range each
        macro was judged against, so the lint recomputes the verdict from the
        TOTAL row against those bounds instead of reading its words only."""
        self.closed(DAY + ON_TARGET)
        self.assertClean()
        one_off = ON_TARGET.replace("69 P (66-72)", "75 P (71-79)") \
            .replace("- protein 0 under", "- protein 6 under").replace("on target", "off target: protein low")
        self.closed(DAY + one_off)
        self.assertClean()
        self.closed(DAY + SUMMARY)
        self.assertClean()

    def test_a_verdict_that_contradicts_the_stored_bounds_fails(self):
        """PR #32 review round 2, item 2: a verdict the stored bounds do not
        give fails, whichever way round it is wrong."""
        self.closed(DAY + ON_TARGET.replace("on target", "off target: protein low"))
        self.assertError("verdict")
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low", "on target"))
        self.assertError("verdict")
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low",
                                          "off target: kcal low, protein low, fat low"))
        self.assertError("verdict")

    def test_an_off_target_verdict_names_the_macros_in_the_column_order(self):
        """The lint recomputes the verdict, so it has one spelling: the off
        macros in the column order of the bullets (PR #32 review round 2)."""
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low",
                                          "off target: protein low, kcal low, fat low, carbs low"))
        self.assertError("verdict")

    def test_a_verdict_names_two_off_macros_in_the_column_order(self):
        """PR #32 review round 2, item 4: two macros off give one entry each, in
        the column order of the bullets, and that Summary is clean."""
        self.closed(DAY + TWO_OFF)
        self.assertClean()

    def test_a_verdict_names_each_macro_at_most_once(self):
        """PR #32 review round 2, item 4: the verdict holds one entry per off
        macro, so a macro named twice fails, whichever directions the two
        entries carry. The weekly review counts these entries for its most
        common miss, so a repeated macro would inflate the count."""
        for verdict in ("off target: protein low, protein low",
                        "off target: protein low, protein high",
                        # The repeated macro is off for real, the rest of the
                        # verdict is right: the repeat alone fails it.
                        "off target: kcal low, fat low, fat low"):
            with self.subTest(verdict=verdict):
                self.closed(DAY + TWO_OFF.replace("off target: kcal low, fat low", verdict))
                self.assertError("at most once")

    def test_two_off_macros_out_of_the_column_order_fail(self):
        """PR #32 review round 2, item 4: the column order holds for a verdict of
        two entries too, so the file has one spelling."""
        self.closed(DAY + TWO_OFF.replace("off target: kcal low, fat low", "off target: fat low, kcal low"))
        self.assertError("verdict")

    def test_the_verdict_holds_when_todays_goals_differ_from_the_snapshot(self):
        """PR #32 review round 2, item 2 and spec #22 story 13: the Summary keeps
        the goal comparison it was closed with, so a later goal change leaves an
        old Day valid. The lint judges it against the stored snapshot only."""
        self.vault.write("nodes/goals/Goals.md", GOALS_B)
        self.closed(DAY)
        self.assertClean()

    def test_an_off_target_verdict_names_low_or_high(self):
        """Spec #22: `off target:` plus each macro that is off and `low` or `high`."""
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low", "off target: protein"))
        self.assertError("low")

    def test_the_verdict_names_the_four_macro_words_only(self):
        self.closed(DAY + SUMMARY.replace("off target: kcal low, protein low, fat low, carbs low", "off target: protein_g low"))
        self.assertError("verdict")

    def test_a_macro_is_low_under_its_stored_min_and_high_over_its_stored_max(self):
        """`high` is a macro over its stored max, `low` one under its stored min;
        the bullet direction follows, because the bounds sit around the target."""
        self.closed(DAY + SUMMARY.replace("protein low", "protein high"))
        self.assertError("protein")
        # The Goals used at close were lower, so kcal and carbs sit over their max.
        over = SUMMARY.replace(GOAL_LINE, "Goal 1000 kcal (950-1050), 135 P (128-142), 60 F (57-63), 200 C (190-210).") \
            .replace("- kcal 1193 under", "- kcal 307 over").replace("- carbs 106 under", "- carbs 49 over") \
            .replace("off target: kcal low, protein low, fat low, carbs low", "off target: kcal high, protein low, fat low, carbs high")
        self.closed(DAY + over)
        self.assertClean()

    # --- the Summary shape (#26) -----------------------------------------------------

    def test_the_summary_needs_the_total_row(self):
        self.closed(DAY + SUMMARY.replace("| TOTAL | ~1307 | ~69 | ~4 | ~249 |\n", ""))
        self.assertError("TOTAL")

    def test_the_total_row_equals_the_day_totals(self):
        self.closed(DAY + SUMMARY.replace("| TOTAL | ~1307 |", "| TOTAL | ~1300 |"))
        self.assertError("TOTAL")
        self.closed(DAY + SUMMARY.replace("| ~69 | ~4 | ~249 |", "| ~69 | ~5 | ~249 |"))
        self.assertError("TOTAL")

    def test_a_slot_row_equals_the_slot_lines(self):
        self.closed(DAY + SUMMARY.replace("| lunch | ~528 |", "| lunch | ~500 |"))
        self.assertError("lunch")

    def test_slot_rows_are_the_present_slots_in_order(self):
        no_snack = DAY.replace("## Snack\n\n" + SNACK + "\n\n", "").replace("kcal: 1307", "kcal: 1136") \
            .replace("protein_g: 69", "protein_g: 63").replace("fat_g: 4", "fat_g: 3").replace("carbs_g: 249", "carbs_g: 211") \
            .replace("fiber_g: 8.8", "fiber_g: 2.5").replace("sugar_g: 16.7", "sugar_g: 16.5").replace("estimated: true", "estimated: false")
        summary = PLAIN_SUMMARY.replace("| snack | 176 | 4 | 0 | 39 |\n", "") \
            .replace("| TOTAL | 1312 | 67 | 3 | 250 |", "| TOTAL | 1136 | 63 | 3 | 211 |") \
            .replace("kcal 1188 under", "kcal 1364 under").replace("protein 68 under", "protein 72 under") \
            .replace("carbs 105 under", "carbs 144 under")
        self.closed(no_snack + summary)
        self.assertClean()
        self.closed(no_snack + summary.replace("| lunch |", "| snack |"))
        self.assertError("snack")
        swapped = summary.replace("| breakfast | 240 | 15 | 1 | 43 |\n| lunch | 528 | 11 | 1 | 117 |", "| lunch | 528 | 11 | 1 | 117 |\n| breakfast | 240 | 15 | 1 | 43 |")
        self.closed(no_snack + swapped)
        self.assertError("order")

    def test_the_table_header_and_its_separator_row_are_fixed(self):
        self.closed(DAY + SUMMARY.replace("| --- | --- | --- | --- | --- |\n", ""))
        self.assertError("---")
        self.closed(DAY + SUMMARY.replace("| slot | kcal | P | F | C |", "| Slot | kcal | protein | fat | carbs |"))
        self.assertError("| slot | kcal | P | F | C |")

    def test_the_separator_row_is_the_one_fixed_five_cell_row(self):
        """PR #32 review round 3, item 4: the lint error and the spec name one
        separator row, `| --- | --- | --- | --- | --- |`, so only that row passes.
        A row with four or six cells, or with dashes of another length, fails,
        because the table has five columns and one spelling."""
        for row in ("| --- | --- | --- | --- |",
                    "| --- | --- | --- | --- | --- | --- |",
                    "| - | - | - | - | - |",
                    "| ---- | ---- | ---- | ---- | ---- |",
                    "|---|---|---|---|---|"):
            with self.subTest(row=row):
                self.closed(DAY + SUMMARY.replace(SUMMARY_SEPARATOR, row))
                self.assertError(SUMMARY_SEPARATOR)
        self.closed(DAY + SUMMARY)
        self.assertClean()

    def test_the_mark_sits_on_every_total_exactly_when_the_day_is_estimated(self):
        """Acceptance #26: `~` before every Summary total of an estimated Day, and
        nowhere on a plain one."""
        self.closed(DAY + SUMMARY.replace("| TOTAL | ~1307 |", "| TOTAL | 1307 |"))
        self.assertError("~")
        self.closed(DAY + SUMMARY.replace("| lunch | ~528 |", "| lunch | 528 |"))
        self.assertError("~")
        self.closed(PLAIN_DAY.replace("estimated: true", "estimated: false") + PLAIN_SUMMARY.replace("| TOTAL | 1312 |", "| TOTAL | ~1312 |"))
        self.assertError("~")
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(PLAIN_DAY.replace("estimated: true", "estimated: false"), status=status)
                self.assertClean()

    def test_the_summary_needs_the_goal_line(self):
        self.closed(DAY + SUMMARY.replace(GOAL_LINE + "\n", ""))
        self.assertError("Goal")
        self.closed(DAY + SUMMARY.replace(GOAL_LINE, "Goal 2500 kcal (2375-2625)."))
        self.assertError("Goal")

    def test_the_goal_line_records_the_targets_used_not_todays_goals(self):
        """Glossary, goal change: each closed Day Summary records the targets it
        used, so a later goal change leaves it valid."""
        self.closed(DAY + SUMMARY.replace("Goal 2500 kcal", "Goal 2400 kcal").replace("kcal 1193 under", "kcal 1093 under"))
        self.assertClean()

    def test_every_target_of_the_goal_line_carries_its_range(self):
        """PR #32 review round 2, item 2: the four targets alone do not carry the
        verdict, so every target on the goal line is followed by the min and the
        max it was judged against, and the lint requires all four."""
        self.closed(DAY + SUMMARY.replace(GOAL_LINE, "Goal 2500 kcal, 135 P, 60 F, 355 C."))
        self.assertError("Goal")
        self.closed(DAY + SUMMARY.replace(GOAL_LINE, "Goal 2500 kcal (2375-2625), 135 P, 60 F, 355 C."))
        self.assertError("Goal")
        self.closed(DAY + SUMMARY.replace("(2375-2625)", "(2375)"))
        self.assertError("Goal")

    def test_a_stored_range_runs_from_the_min_to_the_max_around_its_target(self):
        """The snapshot is a Goals range, so each pair holds its own target:
        `<macro>_min` <= target <= `<macro>_max`. A swapped or drifted pair is a
        broken snapshot, not a verdict the lint can judge."""
        self.closed(DAY + SUMMARY.replace("(2375-2625)", "(2625-2375)"))
        self.assertError("kcal")
        self.closed(DAY + SUMMARY.replace("(128-142)", "(136-142)"))
        self.assertError("protein")

    def test_the_summary_needs_four_macro_bullets_in_order(self):
        self.closed(DAY + SUMMARY.replace("- fat 56 under\n", ""))
        self.assertError("bullet")
        self.closed(DAY + SUMMARY.replace("- protein 66 under\n- fat 56 under", "- fat 56 under\n- protein 66 under"))
        self.assertError("bullet")
        self.closed(DAY + SUMMARY.replace("- protein 66 under", "- protein_g 66 under"))
        self.assertError("bullet")

    def test_a_macro_bullet_is_the_total_against_the_goal_line(self):
        self.closed(DAY + SUMMARY.replace("- kcal 1193 under", "- kcal 1200 under"))
        self.assertError("kcal")
        self.closed(DAY + SUMMARY.replace("- kcal 1193 under", "- kcal 1193 over"))
        self.assertError("kcal")

    def test_a_goal_line_target_may_carry_decimals(self):
        """Review item 5 on PR #32: Goals `kcal`, `protein_g`, `fat_g` and `carbs_g`
        are `number`, not integer, so a target such as 135.5 P is valid and its
        bullet carries the decimal gap. The bullet arithmetic is decimal, so 69
        against 135.5 is exactly 66.5."""
        decimals = SUMMARY.replace("Goal 2500 kcal (2375-2625), 135 P (128-142)", "Goal 2500.5 kcal (2375-2625), 135.5 P (128-142)") \
            .replace("- kcal 1193 under", "- kcal 1193.5 under").replace("- protein 66 under", "- protein 66.5 under")
        self.closed(DAY + decimals)
        self.assertClean()
        self.closed(DAY + decimals.replace("- protein 66.5 under", "- protein 66 under"))
        self.assertError("protein")
        # A whole target gives a whole gap: the gap has one spelling, the shortest.
        self.closed(DAY + SUMMARY.replace("- protein 66 under", "- protein 66.0 under"))
        self.assertError("protein")

    def test_an_exact_hit_writes_zero_under_and_never_zero_over(self):
        """Review item 7 on PR #32: for a macro that hits its target exactly the one
        canonical bullet is `- <macro> 0 under`; `0 over` fails."""
        # kcal sits on its target, so the verdict does not name kcal either.
        exact = SUMMARY.replace("Goal 2500 kcal (2375-2625)", "Goal 1307 kcal (1242-1372)") \
            .replace("- kcal 1193 under", "- kcal 0 under") \
            .replace("off target: kcal low, protein low", "off target: protein low")
        self.closed(DAY + exact)
        self.assertClean()
        self.closed(DAY + exact.replace("- kcal 0 under", "- kcal 0 over"))
        self.assertError("0 under")
        self.closed(DAY + exact.replace("- kcal 0 under", "- kcal 0.0 under"))
        self.assertError("0 under")

    def test_the_hint_is_optional_and_one_line(self):
        self.closed(DAY + SUMMARY.replace("Hint: more protein at lunch.\n", ""))
        self.assertClean()
        self.closed(DAY + SUMMARY + "Hint: and less rice.\n")
        self.assertError("Hint")
        self.closed(DAY + SUMMARY.replace("Hint: more protein at lunch.", "Eat more protein at lunch."))
        self.assertError("Summary")

    def test_the_summary_order_is_table_goal_bullets_verdict_hint(self):
        moved = SUMMARY.replace(GOAL_LINE + "\n\n", "").replace("\nHint:", f"\n{GOAL_LINE}\n\nHint:")
        self.closed(DAY + moved)
        self.assertError("Summary")

    def test_a_log_into_a_closed_day_keeps_the_summary_consistent(self):
        """Acceptance #26: a log into a closed Day rewrites totals and Summary and
        keeps the status; a rewritten Day whose Summary was not rewritten fails."""
        self.closed(CORRECTED_DAY + SUMMARY)
        self.assertError("lunch")
        summary = corrected_table(SUMMARY) \
            .replace("kcal 1193 under", "kcal 1369 under").replace("protein 66 under", "protein 70 under").replace("carbs 106 under", "carbs 145 under")
        self.closed(CORRECTED_DAY + summary)
        self.assertClean()

    def test_refresh_keeps_historical_goals_snapshot(self):
        """PR #32 review round 2, item 2, the whole scenario at the seam.

        The Day is closed under Goals A; the user then changes the Goals to B; a
        later log corrects the Day, and the refresh of `routines/close-day.md`
        rebuilds the Summary. The corrected totals are judged against the stored
        snapshot A, which the file still carries, and never against today's B.

        The lint runs no routine, so it holds the file half of the invariant: a
        Summary whose verdict comes from today's Goals while the stored snapshot
        is the old one fails here. That the refresh reuses the snapshot and
        leaves the status and `open_day` alone is pinned next door, in
        `lint/test_routine_contracts_close_review.py`.
        """
        corrected = corrected_table(SUMMARY) \
            .replace("kcal 1193 under", "kcal 1369 under").replace("protein 66 under", "protein 70 under") \
            .replace("carbs 106 under", "carbs 145 under")
        self.vault.write("nodes/goals/Goals.md", GOALS_B)
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(CORRECTED_DAY + corrected, status=status)
                self.assertClean()
                # The refresh rewrites the Summary only: the status the close
                # wrote and the cleared `open_day` of the State stand.
                self.assertIn(f"status: {status}", (self.vault.root / "nodes/day/2026-09/2026-09-15.md").read_text())
                self.assertIn('open_day: ""', (self.vault.root / "state.md").read_text())
        # The same corrected Day with the verdict taken from today's Goals B,
        # where 4 g of fat sits inside 4 to 4: the stored snapshot A says `fat
        # low`, so the rewritten history fails.
        from_today = corrected.replace("off target: kcal low, protein low, fat low, carbs low",
                                       "off target: kcal low, protein low, carbs low")
        self.closed(CORRECTED_DAY + from_today)
        self.assertError("verdict")

    def test_a_correction_into_an_old_day_keeps_the_newer_open_day_and_the_state(self):
        """PR #32 review round 3, item 3.

        The scenario the older refresh test could not reach: a Day is closed,
        a newer Day is already open, and only then does the correction arrive.
        `test_refresh_keeps_historical_goals_snapshot` closes through `closed()`,
        which empties the State, so it says nothing about a live `open_day`.

        Here `2026-09-15` is closed (and auto-closed in the second round),
        `2026-09-16` is open and the State names it. The correction changes the
        lunch amount of the old Day, and the refresh of `routines/close-day.md`
        rewrites its totals, slot table, TOTAL row, bullets and verdict from the
        goal line the close stored: `on target` becomes `off target`. The lint
        runs no routine, so the fixture is the result the refresh must produce
        and the lint holds the file half: the old Day carries the corrected
        Summary under the stored ranges, its status stands, the newer Day is
        untouched byte for byte and the State still points at it.
        """
        newer_rel = "nodes/day/2026-09/2026-09-16.md"
        newer = DAY.replace("2026-09-15", "2026-09-16")
        newer_state = OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: "[[2026-09-16]]"') \
            .replace("updated: 2026-09-15", "updated: 2026-09-16")
        # 1131 kcal, 65 P, 4 F, 210 C against the stored 1307 (1242-1372), 69
        # (66-72), 4 (4-4), 249 (237-261): fat still sits in its range, the other
        # three fall out of theirs.
        corrected_summary = corrected_table(ON_TARGET) \
            .replace("- kcal 0 under", "- kcal 176 under").replace("- protein 0 under", "- protein 4 under") \
            .replace("- carbs 0 under", "- carbs 39 under") \
            .replace("on target", "off target: kcal low, protein low, carbs low")
        # Today's Goals moved after the close; the refresh must not read them.
        self.vault.write("nodes/goals/Goals.md", GOALS_B)
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.day((DAY + ON_TARGET).replace("status: open", f"status: {status}"))
                self.vault.write(newer_rel, newer)
                self.vault.write("state.md", newer_state)
                self.assertClean()
                before = (self.vault.root / newer_rel).read_bytes()
                # The result the refresh writes: the old Day only.
                self.day((CORRECTED_DAY + corrected_summary).replace("status: open", f"status: {status}"))
                self.assertClean()
                old = (self.vault.root / "nodes/day/2026-09/2026-09-15.md").read_text()
                self.assertIn("kcal: 1131", old)
                self.assertIn("| lunch | ~352 | ~7 | ~1 | ~78 |", old)
                self.assertIn("| TOTAL | ~1131 | ~65 | ~4 | ~210 |", old)
                self.assertIn("- kcal 176 under", old)
                self.assertIn("off target: kcal low, protein low, carbs low", old)
                self.assertIn(ON_TARGET_GOAL_LINE, old)
                self.assertIn(f"status: {status}", old)
                self.assertEqual((self.vault.root / newer_rel).read_bytes(), before)
                self.assertIn("status: open", (self.vault.root / newer_rel).read_text())
                self.assertIn('open_day: "[[2026-09-16]]"', (self.vault.root / "state.md").read_text())
                # The same correction with the Summary of the close left in
                # place: the fixture above passes because the Summary was
                # rebuilt, not by accident.
                self.day((CORRECTED_DAY + ON_TARGET).replace("status: open", f"status: {status}"))
                self.assertError("lunch")


    # --- State and Index -----------------------------------------------------------

    def test_state_must_point_to_the_open_day(self):
        self.vault.write("state.md", OPEN_STATE.replace('open_day: "[[2026-09-15]]"', 'open_day: ""'))
        self.assertError("open_day")

    def test_the_state_open_day_is_empty_when_no_day_is_open(self):
        """Acceptance #26: close-day clears the State in the same step; a closed
        or auto-closed Day the State still names fails."""
        for status in ("closed", "auto-closed"):
            with self.subTest(status=status):
                self.closed(status=status)
                self.vault.write("state.md", OPEN_STATE)
                self.assertError("open_day")

    def test_two_open_days_fail(self):
        second = DAY.replace("2026-09-15", "2026-09-16")
        self.vault.write("nodes/day/2026-09/2026-09-16.md", second)
        self.assertError("open")

    def test_an_auto_closed_day_and_one_open_day_pass(self):
        older = (DAY + SUMMARY).replace("2026-09-15", "2026-09-14").replace("status: open", "status: auto-closed")
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

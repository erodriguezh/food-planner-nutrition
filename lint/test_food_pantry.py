"""Tests for the Food and Pantry lint rules and routine functions (#24).

Run: python3 -m unittest discover lint
"""
import unittest

from test_vault_lint import VaultFixture, INDEX
from vault_lint import (
    lint_vault,
    per_100g_from_per_100ml,
    round_food_value,
    mark_reviewed,
    normalize_alias,
    resolve_name,
    parse_alias_table,
    parse_pantry_item,
    format_pantry_item,
    apply_pantry_change,
    apply_restock,
)

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
sugar_g_per_100g: 4
salt_g_per_100g: 0.1
servings:
  - "1 portion = 200 g"
label_basis: 100g
number_source: database
source_ref: https://world.openfoodfacts.org/product/4061462615481
source_date: 2026-09-15
reviewed: false
---
"""

SOJA = """---
type: food
name: Soy milk Alpro
aliases:
  - Sojadrink Original
  - soy milk
label_name: Sojadrink Original
brand: Alpro
category: drink
kcal_per_100g: 39
protein_g_per_100g: 3
fat_g_per_100g: 1.8
carbs_g_per_100g: 2.5
servings:
  - "1 glass = 250 g"
label_basis: 100ml
density_g_per_ml: 1.0
density_source: estimate
number_source: label
source_date: 2026-09-15
reviewed: true
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
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""

PANTRY = """---
type: pantry
name: Pantry
updated: 2026-09-15
staples:
  - "[[Rice]]"
items:
  - "[[Skyr]] = 1000 g"
  - "[[Soy milk Alpro]] = 1000 g, until 2026-09-20"
---
"""

FOOD_INDEX = (
    "## Food\n"
    "- [[Skyr]] | dairy | skyr natur\n"
    "- [[Soy milk Alpro]] | drink | Sojadrink Original, soy milk\n"
    "- [[Rice]] | grain | Reis\n"
)
INDEX_WITH_FOODS = INDEX.replace("## Food\n", FOOD_INDEX).replace("## Pantry\n", "## Pantry\n- [[Pantry]]\n")


class FoodPantryFixture(VaultFixture):
    def __init__(self):
        super().__init__()
        self.write("nodes/food/Skyr.md", SKYR)
        self.write("nodes/food/Soy milk Alpro.md", SOJA)
        self.write("nodes/food/Rice.md", RICE)
        self.write("nodes/pantry/Pantry.md", PANTRY)
        self.write("index.md", INDEX_WITH_FOODS)


class FoodPantryLintTest(unittest.TestCase):
    def setUp(self):
        self.vault = FoodPantryFixture()

    def tearDown(self):
        self.vault.cleanup()

    def errors(self):
        return lint_vault(self.vault.root)

    def assertError(self, needle):
        errors = self.errors()
        self.assertTrue(any(needle in e for e in errors), f"expected an error containing {needle!r}, got {errors}")

    def food(self, text):
        self.vault.write("nodes/food/Skyr.md", text)

    # --- green path -----------------------------------------------------

    def test_clean_food_and_pantry_pass(self):
        self.assertEqual(self.errors(), [])

    # --- Food required properties and enums ----------------------------

    def test_food_missing_required_property_fails(self):
        self.food(SKYR.replace("category: dairy\n", ""))
        self.assertError("category")

    def test_food_missing_macro_fails(self):
        self.food(SKYR.replace("fat_g_per_100g: 0.2\n", ""))
        self.assertError("fat_g_per_100g")

    def test_food_macro_must_be_number(self):
        self.food(SKYR.replace("kcal_per_100g: 64", "kcal_per_100g: some"))
        self.assertError("kcal_per_100g")

    def test_food_category_enum(self):
        self.food(SKYR.replace("category: dairy", "category: yoghurt"))
        self.assertError("category")

    def test_food_number_source_enum(self):
        self.food(SKYR.replace("number_source: database", "number_source: guess"))
        self.assertError("number_source")

    def test_food_label_basis_enum(self):
        self.food(SKYR.replace("label_basis: 100g", "label_basis: 1kg"))
        self.assertError("label_basis")

    def test_food_reviewed_must_be_checkbox(self):
        self.food(SKYR.replace("reviewed: false", "reviewed: no"))
        self.assertError("reviewed")

    def test_food_source_date_must_be_date(self):
        self.food(SKYR.replace("source_date: 2026-09-15", "source_date: today"))
        self.assertError("source_date")

    def test_food_unknown_property_fails(self):
        self.food(SKYR.replace("reviewed: false", "reviewed: false\nverified: true"))
        self.assertError("verified")

    # --- label_name is one of the aliases -------------------------------

    def test_food_label_name_must_be_listed_in_aliases(self):
        # #22: the aliases list includes the label name.
        self.vault.write("nodes/food/Soy milk Alpro.md", SOJA.replace("  - Sojadrink Original\n", ""))
        self.assertError("label_name")

    def test_food_label_name_without_any_aliases_fails(self):
        self.vault.write(
            "nodes/food/Soy milk Alpro.md",
            SOJA.replace("aliases:\n  - Sojadrink Original\n  - soy milk\n", ""),
        )
        self.assertError("label_name")

    def test_food_label_name_in_aliases_passes(self):
        self.assertEqual(self.errors(), [])

    def test_food_body_allows_notes_only(self):
        self.food(SKYR + "\n## Notes\n\nGood.\n")
        self.assertEqual(self.errors(), [])
        self.food(SKYR + "\n## Label\n\n64 kcal\n")
        self.assertError("Notes")

    def test_food_empty_body_passes(self):
        self.food(SKYR)
        self.assertEqual(self.errors(), [])

    def test_food_free_prose_without_a_heading_fails(self):
        self.food(SKYR + "\nBought at the corner shop.\n")
        self.assertError("Notes")

    def test_food_prose_before_the_notes_heading_fails(self):
        self.food(SKYR + "\nBought at the corner shop.\n\n## Notes\n\nGood.\n")
        self.assertError("Notes")

    def test_food_second_notes_heading_fails(self):
        self.food(SKYR + "\n## Notes\n\nGood.\n\n## Notes\n\nAlso good.\n")
        self.assertError("Notes")

    def test_food_level_one_heading_fails(self):
        self.food(SKYR + "\n# Skyr\n\n## Notes\n\nGood.\n")
        self.assertError("Notes")

    def test_food_level_three_heading_fails(self):
        self.food(SKYR + "\n## Notes\n\n### Taste\n\nSour.\n")
        self.assertError("Notes")

    def test_food_notes_heading_without_content_passes(self):
        self.food(SKYR + "\n## Notes\n")
        self.assertEqual(self.errors(), [])

    # --- density rules --------------------------------------------------

    def test_100ml_needs_density(self):
        self.vault.write("nodes/food/Soy milk Alpro.md", SOJA.replace("density_g_per_ml: 1.0\n", "").replace("density_source: estimate\n", ""))
        self.assertError("density_g_per_ml")

    def test_density_needs_density_source(self):
        self.vault.write("nodes/food/Soy milk Alpro.md", SOJA.replace("density_source: estimate\n", ""))
        self.assertError("density_source")

    def test_density_source_without_density_fails(self):
        self.food(SKYR.replace("label_basis: 100g", "label_basis: 100g\ndensity_source: label"))
        self.assertError("density_source")

    def test_density_source_enum(self):
        self.vault.write("nodes/food/Soy milk Alpro.md", SOJA.replace("density_source: estimate", "density_source: guess"))
        self.assertError("density_source")

    # --- servings -------------------------------------------------------

    def test_serving_must_end_in_grams(self):
        self.food(SKYR.replace('"1 portion = 200 g"', '"1 glass = 250 ml"'))
        self.assertError("servings")

    def test_serving_shape(self):
        self.food(SKYR.replace('"1 portion = 200 g"', '"portion 200 g"'))
        self.assertError("servings")

    def test_serving_with_decimal_count_and_two_word_unit_passes(self):
        self.food(SKYR.replace('"1 portion = 200 g"', '"0.5 small cup = 100 g"'))
        self.vault.write("index.md", INDEX_WITH_FOODS)
        self.assertEqual(self.errors(), [])

    # --- estimated_from -------------------------------------------------

    def test_estimated_from_must_link_existing_food(self):
        self.food(SKYR.replace("number_source: database", 'number_source: estimate\nestimated_from: "[[Quark]]"'))
        self.assertError("estimated_from")

    def test_estimated_from_to_food_passes(self):
        self.food(SKYR.replace("number_source: database", 'number_source: estimate\nestimated_from: "[[Rice]]"'))
        self.assertEqual(self.errors(), [])

    def test_estimate_without_estimated_from_fails(self):
        self.food(SKYR.replace("number_source: database", "number_source: estimate"))
        self.assertError("estimated_from")

    def test_estimated_from_with_label_numbers_keeps_provenance(self):
        # Provenance stays after a label fix: `estimated_from` may outlive the estimate.
        self.food(SKYR.replace("number_source: database", 'number_source: label\nestimated_from: "[[Rice]]"'))
        self.assertEqual(self.errors(), [])

    def test_estimated_from_with_database_numbers_keeps_provenance(self):
        self.food(SKYR.replace("number_source: database", 'number_source: database\nestimated_from: "[[Rice]]"'))
        self.assertEqual(self.errors(), [])

    def test_food_number_with_two_decimals_fails(self):
        self.food(SKYR.replace("salt_g_per_100g: 0.1", "salt_g_per_100g: 0.075"))
        self.assertError("rounding rule")

    def test_density_may_have_two_decimals(self):
        self.food(SKYR.replace("label_basis: 100g", "label_basis: 100g\ndensity_g_per_ml: 0.91\ndensity_source: database"))
        self.assertEqual(self.errors(), [])

    def test_estimated_from_must_be_wikilink(self):
        self.food(SKYR.replace("number_source: database", "number_source: estimate\nestimated_from: Rice"))
        self.assertError("estimated_from")

    # --- Pantry ---------------------------------------------------------

    def test_pantry_must_be_the_one_file(self):
        self.vault.write("nodes/pantry/Pantry.md", "")
        import os
        os.remove(self.vault.root / "nodes/pantry/Pantry.md")
        self.vault.write("nodes/pantry/Kitchen.md", PANTRY.replace("name: Pantry", "name: Kitchen"))
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("[[Pantry]]", "[[Kitchen]]"))
        self.assertError("Pantry.md")

    def test_pantry_missing_updated_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace("updated: 2026-09-15\n", ""))
        self.assertError("updated")

    def test_pantry_unknown_property_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace("updated: 2026-09-15", "updated: 2026-09-15\nlocation: home"))
        self.assertError("location")

    def test_pantry_link_to_missing_node_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Quark]] = 500 g"'))
        self.assertError("Quark")

    def test_pantry_staple_must_be_link_only(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Rice]]"', '"[[Rice]] = 1000 g"'))
        self.assertError("staples")

    def test_pantry_staple_must_be_food(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Rice]]"', '"[[Goals]]"'))
        self.assertError("staples")

    def test_pantry_item_shape(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] 1000 g"'))
        self.assertError("items")

    def test_pantry_food_item_amount_is_grams(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] = 2 cups"'))
        self.assertError("items")

    def test_pantry_food_item_cannot_be_portion(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] = 2 portion"'))
        self.assertError("items")

    def test_pantry_until_must_be_date(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace("until 2026-09-20", "until Friday"))
        self.assertError("items")

    def test_pantry_item_without_amount_passes(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]]"'))
        self.assertEqual(self.errors(), [])

    def test_pantry_item_until_without_amount_passes(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]], until 2026-09-18"'))
        self.assertEqual(self.errors(), [])

    def test_pantry_duplicate_link_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Rice]]"', '"[[Rice]]"\n  - "[[Skyr]]"'))
        self.assertError("twice")

    def test_pantry_meal_item_in_portions_passes(self):
        self.vault.write(
            "nodes/meal/Chili.md",
            "---\ntype: meal\nname: Chili\n---\n",
        )
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] = 1000 g"\n  - "[[Chili]] = 2 portion, until 2026-09-19"'))
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("## Meal\n", "## Meal\n- [[Chili]] | dinner\n"))
        self.assertEqual(self.errors(), [])

    def test_pantry_meal_item_in_cooked_grams_passes(self):
        self.vault.write("nodes/meal/Chili.md", "---\ntype: meal\nname: Chili\n---\n")
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] = 1000 g"\n  - "[[Chili]] = 300 g cooked"'))
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("## Meal\n", "## Meal\n- [[Chili]] | dinner\n"))
        self.assertEqual(self.errors(), [])

    def test_pantry_meal_item_in_plain_grams_fails(self):
        self.vault.write("nodes/meal/Chili.md", "---\ntype: meal\nname: Chili\n---\n")
        self.vault.write("nodes/pantry/Pantry.md", PANTRY.replace('"[[Skyr]] = 1000 g"', '"[[Skyr]] = 1000 g"\n  - "[[Chili]] = 300 g"'))
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("## Meal\n", "## Meal\n- [[Chili]] | dinner\n"))
        self.assertError("Chili")

    def test_pantry_body_allows_notes_only(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY + "\n## Shopping\n\n- milk\n")
        self.assertError("Notes")

    def test_pantry_notes_body_passes(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY + "\n## Notes\n\nSeeded today.\n")
        self.assertEqual(self.errors(), [])

    def test_pantry_free_prose_without_a_heading_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY + "\nI still need milk.\n")
        self.assertError("Notes")

    def test_pantry_second_notes_heading_fails(self):
        self.vault.write("nodes/pantry/Pantry.md", PANTRY + "\n## Notes\n\nOne.\n\n## Notes\n\nTwo.\n")
        self.assertError("Notes")

    # --- Index Food lines -----------------------------------------------

    def test_food_index_line_needs_category(self):
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("- [[Rice]] | grain | Reis\n", "- [[Rice]]\n"))
        self.assertError("Rice")

    def test_food_index_line_category_must_match(self):
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("- [[Rice]] | grain | Reis\n", "- [[Rice]] | protein | Reis\n"))
        self.assertError("grain")

    def test_food_index_line_must_list_all_aliases(self):
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("| Sojadrink Original, soy milk\n", "| soy milk\n"))
        self.assertError("Sojadrink Original")

    def test_food_index_line_must_not_invent_aliases(self):
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("| Reis\n", "| Reis, Risotto\n"))
        self.assertError("Risotto")

    def test_food_index_line_includes_label_name(self):
        # The label name is one of the aliases, so the Index line must carry it.
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("| Sojadrink Original, soy milk\n", "| soy milk\n"))
        self.assertError("Sojadrink Original")

    def test_food_without_aliases_has_link_and_category_only(self):
        self.vault.write("nodes/food/Rice.md", RICE.replace("aliases:\n  - Reis\n", ""))
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("- [[Rice]] | grain | Reis\n", "- [[Rice]] | grain\n"))
        self.assertEqual(self.errors(), [])

    def test_food_with_two_index_lines_fails(self):
        self.vault.write("index.md", INDEX_WITH_FOODS.replace("- [[Rice]] | grain | Reis\n", "- [[Rice]] | grain | Reis\n- [[Rice]] | grain | Reis\n"))
        self.assertError("one Index line")

    def test_duplicate_base_name_across_food_and_meal_fails(self):
        self.vault.write("nodes/meal/Rice.md", "---\ntype: meal\nname: Rice\n---\n")
        self.assertError("unique")


class FoodRoutineFunctionTest(unittest.TestCase):
    def test_per_100ml_converts_with_density(self):
        # olive oil label per 100 ml: 822 kcal, 91 g fat; density 0.91 g/ml
        result = per_100g_from_per_100ml({"kcal_per_100g": 822, "fat_g_per_100g": 91, "protein_g_per_100g": 0, "carbs_g_per_100g": 0}, 0.91)
        self.assertEqual(result["kcal_per_100g"], 903.3)
        self.assertEqual(result["fat_g_per_100g"], 100)
        self.assertEqual(result["protein_g_per_100g"], 0)

    def test_per_100ml_with_density_one_is_identity(self):
        values = {"kcal_per_100g": 39, "protein_g_per_100g": 3, "fat_g_per_100g": 1.8, "carbs_g_per_100g": 2.5}
        self.assertEqual(per_100g_from_per_100ml(values, 1.0), values)

    def test_round_food_value_one_decimal_half_up(self):
        self.assertEqual(round_food_value(2.25), 2.3)
        self.assertEqual(round_food_value(2.24), 2.2)
        self.assertEqual(round_food_value(64.0), 64)

    def test_mark_reviewed_changes_nothing_else(self):
        before = {"type": "food", "name": "Skyr", "kcal_per_100g": "64", "number_source": "estimate", "reviewed": "false"}
        after = mark_reviewed(before)
        self.assertEqual(after["reviewed"], "true")
        self.assertEqual({k: v for k, v in after.items() if k != "reviewed"}, {k: v for k, v in before.items() if k != "reviewed"})
        self.assertEqual(after["number_source"], "estimate")
        self.assertEqual(before["reviewed"], "false")


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


class PantryRoutineFunctionTest(unittest.TestCase):
    DATA = {
        "type": "pantry",
        "name": "Pantry",
        "updated": "2026-09-14",
        "staples": ["[[Rice]]", "[[Oats]]"],
        "items": ["[[Skyr]] = 1000 g", "[[Chili]] = 2 portion, until 2026-09-19", "[[Blueberries]]"],
    }

    def test_parse_and_format_item_round_trip(self):
        for text in ("[[Skyr]] = 1000 g", "[[Chili]] = 2 portion, until 2026-09-19", "[[Blueberries]]", "[[Chili]] = 300 g cooked", "[[Skyr]], until 2026-09-18"):
            self.assertEqual(format_pantry_item(*parse_pantry_item(text)), text)
        self.assertEqual(parse_pantry_item("[[Skyr]] = 1000 g"), ("Skyr", "1000 g", None))

    def test_bought_new_item_is_appended(self):
        data = apply_pantry_change(self.DATA, ("bought", "Chicken breast", "1000 g", None), "2026-09-15")
        self.assertIn("[[Chicken breast]] = 1000 g", data["items"])
        self.assertEqual(data["updated"], "2026-09-15")
        self.assertEqual(self.DATA["updated"], "2026-09-14")

    def test_bought_existing_item_adds_amounts(self):
        data = apply_pantry_change(self.DATA, ("bought", "Skyr", "500 g", None), "2026-09-15")
        self.assertIn("[[Skyr]] = 1500 g", data["items"])
        self.assertEqual(len(data["items"]), 3)

    def test_bought_with_until_sets_until(self):
        data = apply_pantry_change(self.DATA, ("bought", "Skyr", "500 g", "2026-09-22"), "2026-09-15")
        self.assertIn("[[Skyr]] = 1500 g, until 2026-09-22", data["items"])

    def test_bought_staple_is_ignored(self):
        data = apply_pantry_change(self.DATA, ("bought", "Rice", "1000 g", None), "2026-09-15")
        self.assertEqual(data["items"], self.DATA["items"])
        self.assertEqual(data["staples"], self.DATA["staples"])

    def test_gone_removes_from_either_list(self):
        data = apply_pantry_change(self.DATA, ("gone", "Skyr"), "2026-09-15")
        self.assertFalse(any("[[Skyr]]" in i for i in data["items"]))
        data = apply_pantry_change(self.DATA, ("gone", "Oats"), "2026-09-15")
        self.assertEqual(data["staples"], ["[[Rice]]"])

    def test_make_staple_moves_from_items(self):
        data = apply_pantry_change(self.DATA, ("staple", "Skyr"), "2026-09-15")
        self.assertIn("[[Skyr]]", data["staples"])
        self.assertFalse(any("[[Skyr]]" in i for i in data["items"]))

    def test_make_item_moves_from_staples(self):
        data = apply_pantry_change(self.DATA, ("item", "Oats", "500 g", None), "2026-09-15")
        self.assertNotIn("[[Oats]]", data["staples"])
        self.assertIn("[[Oats]] = 500 g", data["items"])

    def test_restock_sums_and_skips_staples_with_note(self):
        data, notes = apply_restock(
            self.DATA,
            [("Skyr", "1000 g", None), ("Rice", "1000 g", None), ("Chicken breast", "600 g", None)],
            "2026-09-15",
        )
        self.assertIn("[[Skyr]] = 2000 g", data["items"])
        self.assertIn("[[Chicken breast]] = 600 g", data["items"])
        self.assertEqual(data["staples"], self.DATA["staples"])
        self.assertEqual(notes, ["Rice is a staple, not added"])
        self.assertEqual(data["updated"], "2026-09-15")


if __name__ == "__main__":
    unittest.main()

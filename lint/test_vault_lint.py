"""Tests for vault lint v1. Run: python3 -m unittest discover lint"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from vault_lint import lint_vault, round_bound, estimate_tokens

GOALS = """---
type: goals
name: Goals
kcal: 2500
protein_g: 135
fat_g: 60
carbs_g: 355
tolerance_pct: 5
kcal_min: 2375
kcal_max: 2625
protein_g_min: 128
protein_g_max: 142
fat_g_min: 57
fat_g_max: 63
carbs_g_min: 337
carbs_g_max: 373
since: 2026-09-15
---
"""

INDEX = """## Food

## Meal

## Day

## Goals
- [[Goals]]

## Pantry
"""

STATE = """---
type: state
open_day: ""
updated: 2026-09-15
---

## Open items
"""

ROUTER = "# Router\n\nShort router.\n"


class VaultFixture:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "nodes" / "goals").mkdir(parents=True)
        (self.root / "nodes" / "food").mkdir(parents=True)
        (self.root / "nodes" / "meal").mkdir(parents=True)
        (self.root / "nodes" / "pantry").mkdir(parents=True)
        (self.root / "nodes" / "day").mkdir(parents=True)
        (self.root / "routines").mkdir()
        self.write("ROUTER.md", ROUTER)
        self.write("index.md", INDEX)
        self.write("state.md", STATE)
        self.write("nodes/goals/Goals.md", GOALS)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(self.root)


class LintTest(unittest.TestCase):
    def setUp(self):
        self.vault = VaultFixture()

    def tearDown(self):
        self.vault.cleanup()

    def errors(self):
        return lint_vault(self.vault.root)

    def assertError(self, needle):
        errors = self.errors()
        self.assertTrue(
            any(needle in e for e in errors),
            f"expected an error containing {needle!r}, got {errors}",
        )

    # --- green path -----------------------------------------------------

    def test_clean_vault_passes(self):
        self.assertEqual(self.errors(), [])

    # --- rounding rule --------------------------------------------------

    def test_round_bound_half_rounds_up(self):
        self.assertEqual(round_bound(137.5), 138)
        self.assertEqual(round_bound(128.25), 128)
        self.assertEqual(round_bound(141.75), 142)
        self.assertEqual(round_bound(2375.0), 2375)

    def test_token_estimate_is_chars_over_four(self):
        self.assertEqual(estimate_tokens("abcd" * 10), 10)
        self.assertEqual(estimate_tokens("abcde"), 2)

    # --- Goals schema ---------------------------------------------------

    def test_wrong_bound_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("protein_g_max: 142", "protein_g_max: 141"))
        self.assertError("protein_g_max")

    def test_missing_bound_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("fat_g_min: 57\n", ""))
        self.assertError("fat_g_min")

    def test_missing_since_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("since: 2026-09-15\n", ""))
        self.assertError("since")

    def test_since_must_be_a_date(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("since: 2026-09-15", "since: yesterday"))
        self.assertError("since")

    def test_target_must_be_a_number(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("kcal: 2500", "kcal: lots"))
        self.assertError("kcal")

    def test_bounds_follow_tolerance(self):
        goals = GOALS.replace("tolerance_pct: 5", "tolerance_pct: 10")
        self.vault.write("nodes/goals/Goals.md", goals)
        self.assertError("kcal_min")

    # --- common node conventions ----------------------------------------

    def test_name_differs_from_file_name_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("name: Goals", "name: Targets"))
        self.assertError("name")

    def test_missing_type_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("type: goals\n", ""))
        self.assertError("type")

    def test_nested_frontmatter_fails(self):
        nested = GOALS.replace("since: 2026-09-15\n", "since: 2026-09-15\nmeta:\n  nested: 1\n")
        self.vault.write("nodes/goals/Goals.md", nested)
        self.assertError("flat")

    def test_missing_frontmatter_fails(self):
        self.vault.write("nodes/goals/Goals.md", "# Goals\n")
        self.assertError("frontmatter")

    def test_duplicate_base_name_fails(self):
        self.vault.write("nodes/food/Goals.md", GOALS.replace("type: goals", "type: food"))
        self.assertError("unique")

    def test_unknown_type_fails(self):
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("type: goals", "type: target"))
        self.assertError("type")

    # --- Router ---------------------------------------------------------

    def test_router_over_500_tokens_fails(self):
        self.vault.write("ROUTER.md", "word " * 600)
        self.assertError("ROUTER.md")

    def test_missing_router_fails(self):
        os.remove(self.vault.root / "ROUTER.md")
        self.assertError("ROUTER.md")

    # --- State ----------------------------------------------------------

    def test_state_missing_open_items_fails(self):
        self.vault.write("state.md", STATE.replace("## Open items\n", ""))
        self.assertError("Open items")

    def test_state_missing_open_day_fails(self):
        self.vault.write("state.md", STATE.replace('open_day: ""\n', ""))
        self.assertError("open_day")

    def test_state_open_day_must_point_to_open_day_node(self):
        self.vault.write("state.md", STATE.replace('open_day: ""', 'open_day: "[[2026-09-15]]"'))
        self.assertError("open_day")

    def test_state_unreviewed_food_line_fails(self):
        self.vault.write("state.md", STATE + "- Croissant is unreviewed\n")
        self.assertError("unreviewed")

    def test_state_food_link_in_open_items_fails(self):
        self.vault.write("nodes/food/Croissant.md", "---\ntype: food\nname: Croissant\nreviewed: false\n---\n")
        self.vault.write("index.md", INDEX.replace("## Food\n", "## Food\n- [[Croissant]] | grain | Kipferl\n"))
        self.vault.write("state.md", STATE + "- [[Croissant]]\n")
        self.assertError("Food")

    def test_state_updated_must_be_date(self):
        self.vault.write("state.md", STATE.replace("updated: 2026-09-15", "updated: today"))
        self.assertError("updated")

    # --- Index ----------------------------------------------------------

    def test_index_missing_section_fails(self):
        self.vault.write("index.md", INDEX.replace("## Pantry\n", ""))
        self.assertError("Pantry")

    def test_index_line_without_node_fails(self):
        self.vault.write("index.md", INDEX.replace("## Food\n", "## Food\n- [[Ghost]] | grain\n"))
        self.assertError("Ghost")

    def test_index_line_in_wrong_section_fails(self):
        self.vault.write("index.md", INDEX.replace("- [[Goals]]\n", "").replace("## Food\n", "## Food\n- [[Goals]]\n"))
        self.assertError("Goals")

    def test_node_without_index_line_fails(self):
        self.vault.write("index.md", INDEX.replace("- [[Goals]]\n", ""))
        self.assertError("Goals")

    def test_index_day_line_without_folder_fails(self):
        self.vault.write("index.md", INDEX.replace("## Day\n", "## Day\n- 2026-09 | nodes/day/2026-09/\n"))
        self.assertError("2026-09")

    def test_index_day_line_with_folder_passes(self):
        (self.vault.root / "nodes" / "day" / "2026-09").mkdir()
        self.vault.write("index.md", INDEX.replace("## Day\n", "## Day\n- 2026-09 | nodes/day/2026-09/\n"))
        self.assertEqual(self.errors(), [])

    def test_index_free_sentence_fails(self):
        self.vault.write("index.md", INDEX.replace("## Food\n", "## Food\nSome prose here.\n"))
        self.assertError("index.md")

    # --- Routines -------------------------------------------------------

    def test_routine_missing_section_fails(self):
        self.vault.write("routines/goals.md", "# goals\n\n## When\nx\n\n## Read\nx\n\n## Steps\nx\n\n## Write\nx\n")
        self.assertError("Reply")

    def test_routine_with_five_sections_passes(self):
        self.vault.write(
            "routines/goals.md",
            "# goals\n\n## When\nx\n\n## Read\nx\n\n## Steps\nx\n\n## Write\nx\n\n## Reply\nx\n",
        )
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()

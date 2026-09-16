"""Tests for the vault lint. Run: python3 -m unittest discover lint"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from vault_lint import (
    SKILL_FILE,
    apply_goal_change,
    compute_bounds,
    estimate_tokens,
    lint_vault,
    round_bound,
    skill_rule_line,
)

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
- [[Pantry]]
"""

PANTRY_NODE = """---
type: pantry
name: Pantry
updated: 2026-09-15
---
"""

STATE = """---
type: state
open_day: ""
updated: 2026-09-15
---

## Open items
"""

ROUTER = f"# Router\n\n1. Context MCP connected? Call `build_context` first, see `{SKILL_FILE}`. Otherwise read `index.md`.\n2. Read `state.md`.\n"

RULE_LINE = "the one line the skill file quotes."

SKILL = f"""# Context MCP\n\nThe rule for the retrieval service. Connected: call the tool first.\nNot connected: read `index.md`, then `state.md`.\n\n"{RULE_LINE}"\n"""

CROISSANT = """---
type: food
name: Croissant
aliases:
  - Kipferl
category: grain
kcal_per_100g: 406
protein_g_per_100g: 8
fat_g_per_100g: 21
carbs_g_per_100g: 46
label_basis: 100g
number_source: database
source_date: 2026-09-15
reviewed: false
---
"""


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
        self.write(SKILL_FILE, SKILL)
        self.write("AGENTS.md", "Read ROUTER.md first.\n")
        self.write("index.md", INDEX)
        self.write("state.md", STATE)
        self.write("nodes/goals/Goals.md", GOALS)
        self.write("nodes/pantry/Pantry.md", PANTRY_NODE)

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

    def test_a_bound_half_produced_by_the_tolerance_rounds_up(self):
        """Round-3 feedback item 1: the half comes out of the multiplication.

        A target of 1850 with a tolerance of 7 gives exactly 1720.5, which
        stores 1721. In binary floats the product is 1720.4999999999998 and
        stores 1720, so the bounds are computed as decimals.
        """
        bounds = compute_bounds({"kcal": "1850", "protein_g": "135", "fat_g": "60", "carbs_g": "355"}, "7")
        self.assertEqual(bounds["kcal_min"], 1721)
        self.assertEqual(bounds["kcal_max"], 1980)

    def half_bound_goals(self, kcal_min):
        """The Goals node of a 1850 kcal target with a tolerance of 7, whose
        `kcal_min` is the exact half 1720.5. Every other bound is its own
        rounded value."""
        self.vault.write("nodes/goals/Goals.md", GOALS
                         .replace("kcal: 2500", "kcal: 1850")
                         .replace("tolerance_pct: 5", "tolerance_pct: 7")
                         .replace("kcal_min: 2375", f"kcal_min: {kcal_min}")
                         .replace("kcal_max: 2625", "kcal_max: 1980")
                         .replace("protein_g_min: 128", "protein_g_min: 126")
                         .replace("protein_g_max: 142", "protein_g_max: 144")
                         .replace("fat_g_min: 57", "fat_g_min: 56")
                         .replace("fat_g_max: 63", "fat_g_max: 64")
                         .replace("carbs_g_min: 337", "carbs_g_min: 330")
                         .replace("carbs_g_max: 373", "carbs_g_max: 380"))

    def test_a_goals_node_on_a_bound_half_passes(self):
        self.half_bound_goals(1721)
        self.assertEqual(self.errors(), [])

    def test_a_bound_half_rounded_down_fails(self):
        self.half_bound_goals(1720)
        self.assertError("kcal_min")

    def test_token_estimate_is_chars_over_four(self):
        self.assertEqual(estimate_tokens("abcd" * 10), 10)
        self.assertEqual(estimate_tokens("abcde"), 2)

    # --- first violation only ------------------------------------------

    def test_lint_stops_at_first_violation_in_check_order(self):
        # Goals check runs before the Index check, so only the bound error is reported.
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("protein_g_max: 142", "protein_g_max: 141"))
        self.vault.write("index.md", INDEX.replace("## Pantry\n", ""))
        errors = self.errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("protein_g_max", errors[0])
        self.assertNotIn("Pantry", errors[0])

    def test_first_violation_is_deterministic_across_files(self):
        # Two bad nodes: sorted path order puts nodes/food before nodes/goals.
        self.vault.write("nodes/food/Skyr.md", "---\ntype: food\nname: Skyrr\n---\n")
        self.vault.write("nodes/goals/Goals.md", GOALS.replace("name: Goals", "name: Targets"))
        errors = self.errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("nodes/food/Skyr.md", errors[0])

    # --- goals routine as a function -----------------------------------

    def test_first_setup_defaults_tolerance_to_5(self):
        result = apply_goal_change(None, {"kcal": 2500, "protein_g": 135, "fat_g": 60, "carbs_g": 355}, None, "2026-09-15")
        self.assertEqual(result["tolerance_pct"], 5)
        self.assertEqual(result["protein_g_min"], 128)
        self.assertEqual(result["protein_g_max"], 142)
        self.assertEqual(result["since"], "2026-09-15")

    def test_first_setup_needs_all_four_targets(self):
        with self.assertRaises(ValueError):
            apply_goal_change(None, {"kcal": 2500}, None, "2026-09-15")

    def test_partial_change_preserves_stored_tolerance_and_targets(self):
        existing = {"kcal": "2500", "protein_g": "135", "fat_g": "60", "carbs_g": "355", "tolerance_pct": "10"}
        result = apply_goal_change(existing, {"protein_g": 160}, None, "2026-09-16")
        self.assertEqual((result["kcal"], result["protein_g"], result["fat_g"], result["carbs_g"]), (2500, 160, 60, 355))
        self.assertEqual(result["tolerance_pct"], 10)
        self.assertEqual(result["since"], "2026-09-16")
        expected = compute_bounds({"kcal": 2500, "protein_g": 160, "fat_g": 60, "carbs_g": 355}, 10)
        for key, want in expected.items():
            self.assertEqual(result[key], want, key)
        self.assertEqual(result["protein_g_min"], 144)
        self.assertEqual(result["protein_g_max"], 176)
        self.assertEqual(result["kcal_min"], 2250)
        self.assertEqual(result["kcal_max"], 2750)

    def test_tolerance_change_alone_recomputes_all_bounds(self):
        existing = {"kcal": "2500", "protein_g": "135", "fat_g": "60", "carbs_g": "355", "tolerance_pct": "5"}
        result = apply_goal_change(existing, {}, 10, "2026-09-16")
        self.assertEqual(result["protein_g"], 135)
        self.assertEqual(result["tolerance_pct"], 10)
        self.assertEqual(result["fat_g_min"], 54)
        self.assertEqual(result["fat_g_max"], 66)

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

    def test_router_without_the_skill_pointer_fails(self):
        # #27: "The Router has one pointer line to the skill file."
        self.vault.write("ROUTER.md", "# Router\n\n1. Read `index.md`.\n2. Read `state.md`.\n")
        self.assertError(SKILL_FILE)

    def test_router_with_two_skill_pointers_fails(self):
        self.vault.write("ROUTER.md", ROUTER + f"\nSee `{SKILL_FILE}` again.\n")
        self.assertError("one line")

    def test_router_that_repeats_the_rule_line_fails(self):
        # #27: the Router points to the skill file and holds no copy of the rule.
        self.vault.write("ROUTER.md", ROUTER + f'\nWhen it is down say "{RULE_LINE}"\n')
        self.assertError("ROUTER.md")

    # --- Skill file -----------------------------------------------------

    def test_missing_skill_file_fails(self):
        os.remove(self.vault.root / SKILL_FILE)
        self.assertError(SKILL_FILE)

    def test_skill_file_without_a_quoted_rule_line_fails(self):
        # #27 round 2: the contract is not written in this script. The lint
        # derives the line it must not find elsewhere from the skill file.
        self.vault.write(SKILL_FILE, SKILL.replace(f'"{RULE_LINE}"', RULE_LINE))
        self.assertError("exactly one line")

    def test_skill_file_with_two_quoted_lines_fails(self):
        self.vault.write(SKILL_FILE, SKILL + '\n"a second quoted line."\n')
        self.assertError("exactly one line")

    def test_the_lint_reads_the_rule_line_out_of_the_skill_file(self):
        self.assertEqual(skill_rule_line(SKILL), RULE_LINE)
        self.assertIsNone(skill_rule_line("# Context MCP\n\nNo quoted line here.\n"))

    def test_another_file_that_repeats_the_rule_line_fails(self):
        # #27: "No other file in the repo and no app project instruction repeats the rule."
        self.vault.write("AGENTS.md", f"Read ROUTER.md first. If the MCP is down say \"{RULE_LINE}\"\n")
        self.assertError("AGENTS.md")

    def test_the_spec_document_may_state_the_rule_line(self):
        self.vault.write("docs/spec/context-mcp.md", f"# Spec: Context MCP\n\nFallback: \"{RULE_LINE}\"\n")
        self.assertEqual(self.errors(), [])

    def test_another_spec_document_that_repeats_the_rule_line_fails(self):
        self.vault.write("docs/spec/nodes.md", f"# Spec: nodes\n\nFallback: \"{RULE_LINE}\"\n")
        self.assertError("docs/spec/nodes.md")

    def test_missing_agents_file_fails(self):
        # #22 story 3: AGENTS.md holds the one line; every app starts from it.
        os.remove(self.vault.root / "AGENTS.md")
        self.assertError("AGENTS.md")

    def test_agents_file_with_more_than_the_pointer_line_fails(self):
        # #22 story 3: AGENTS.md holds one line, "Read ROUTER.md first."
        self.vault.write("AGENTS.md", "Read ROUTER.md first.\nCall the Context MCP first.\n")
        self.assertError("AGENTS.md")

    def test_agents_file_with_the_one_pointer_line_passes(self):
        self.vault.write("AGENTS.md", "Read ROUTER.md first.\n")
        self.assertEqual(self.errors(), [])

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
        self.vault.write("nodes/food/Croissant.md", CROISSANT)
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

    def test_routine_over_the_token_limit_fails(self):
        # Spec #22, Routines: "Under 300 tokens each." One token is four characters.
        filler = "word " * 250  # 1250 characters, about 313 tokens
        self.vault.write(
            "routines/goals.md",
            f"# goals\n\n## When\nx\n\n## Read\nx\n\n## Steps\n{filler}\n\n## Write\nx\n\n## Reply\nx\n",
        )
        self.assertError("tokens")

    def test_routine_just_under_the_token_limit_passes(self):
        filler = "word " * 200  # 1000 characters, about 264 tokens
        self.vault.write(
            "routines/goals.md",
            f"# goals\n\n## When\nx\n\n## Read\nx\n\n## Steps\n{filler}\n\n## Write\nx\n\n## Reply\nx\n",
        )
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()

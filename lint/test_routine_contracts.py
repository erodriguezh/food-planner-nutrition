"""Contract tests for the routine texts (#24).

The routine files are the contract between the agent and the vault for the
things the lint cannot see: which path the agent takes, how many times it
asks, and what the "ok" step means. These tests read the routine text and
the routine functions together, so text and code cannot drift apart.

Run: python3 -m unittest discover lint
"""
import re
import unittest
from pathlib import Path

from vault_lint import (
    ROUTINE_SECTIONS,
    apply_pantry_change,
    apply_restock,
    estimate_tokens,
    mark_reviewed,
    parse_frontmatter,
    round_food_value,
)

# Spec #22, Routines: "Under 300 tokens each."
ROUTINE_TOKEN_LIMIT = 300

# A metric measuring tablespoon is 15 ml. The old node called a 10 ml spoon a
# `tbsp`, which made every logged spoon of oil too light.
METRIC_TABLESPOON_ML = 15

VAULT = Path(__file__).resolve().parent.parent
CREATE_FOOD = VAULT / "routines" / "create-food.md"
PANTRY = VAULT / "routines" / "pantry.md"
NODES_SPEC = VAULT / "docs" / "spec" / "nodes.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RoutineShapeTest(unittest.TestCase):
    """The two routines this ticket rewrites keep the shape the spec asks for."""

    def test_both_routines_keep_the_five_sections(self):
        for path in (CREATE_FOOD, PANTRY):
            headings = [line[3:].strip() for line in read(path).split("\n") if line.startswith("## ")]
            self.assertEqual(headings, list(ROUTINE_SECTIONS), path.name)

    def test_both_routines_stay_under_the_token_limit(self):
        for path in (CREATE_FOOD, PANTRY):
            tokens = estimate_tokens(read(path))
            self.assertLess(tokens, ROUTINE_TOKEN_LIMIT, f"{path.name} is about {tokens} tokens")


class RoutineTextTestCase(unittest.TestCase):
    def one_line_with(self, text: str, needle: str) -> str:
        """The one line that holds `needle`. Fails when it is absent or repeated."""
        hits = [line for line in text.split("\n") if needle in line]
        self.assertEqual(len(hits), 1, f"expected exactly one line with {needle!r}, found {len(hits)}")
        return hits[0]


class PantryPhotoOneOkTest(RoutineTextTestCase):
    """Story 95: a receipt or shopping-list photo takes exactly one "Ok?" step."""

    def setUp(self):
        self.text = read(PANTRY)

    def test_exactly_one_ok_question_in_the_pantry_routine(self):
        self.assertEqual(len(re.findall(r"Ok\?", self.text)), 1)

    def test_the_shown_list_is_the_add_to_pantry_list(self):
        self.assertIn('"Add to Pantry: ', self.text)

    def test_nothing_is_written_before_that_ok(self):
        self.assertIn("Write nothing before the ok", self.text)

    def test_unknown_foods_are_staged_not_written_on_a_photo(self):
        photo = self.one_line_with(self.text, "Add to Pantry: ")
        self.assertIn("stage", photo.lower())

    def test_the_photo_path_does_not_delegate_to_the_create_food_reply(self):
        """create-food ends in its own "Say ok to mark reviewed."; the photo path must not chain it."""
        self.assertIn("Say ok to mark reviewed.", read(CREATE_FOOD))
        chain = self.one_line_with(self.text, "then follow `routines/create-food.md`")
        self.assertIn("chat form", chain.lower())
        self.assertNotIn("photo", chain.lower())

    def test_the_staged_foods_are_created_after_the_ok_with_their_own_commits(self):
        after = self.one_line_with(self.text, "After the ok")
        self.assertIn("create", after.lower())
        self.assertIn("`create-food: <name>`", self.text)
        self.assertLess(self.text.index("`create-food: <name>`"), self.text.index("`pantry: <one line>`"))

    def test_the_pantry_ok_is_not_a_food_review(self):
        review = self.one_line_with(self.text, "not a Food review")
        self.assertIn("`reviewed: false`", review)
        self.assertNotIn("reviewed: true", self.text)

    def test_staples_in_the_photo_are_skipped_with_a_note(self):
        after = self.one_line_with(self.text, "After the ok")
        self.assertIn("Staples are skipped with a note", after)


class CreateFoodDensityRuleTest(RoutineTextTestCase):
    """Spec #22 Food schema: `density_g_per_ml` with `density_source` is also
    required when a serving was given in ml, so the routine text must say so.
    The lint cannot see the input unit, so this text is the only contract."""

    def setUp(self):
        self.text = read(CREATE_FOOD)

    def test_an_ml_serving_stores_the_density_even_with_a_100g_label(self):
        rule = self.one_line_with(self.text, "`density_source`")
        self.assertIn("ml", rule)
        self.assertIn("`density_g_per_ml`", rule)
        self.assertIn("`label_basis: 100g`", rule)

    def test_the_converted_serving_alias_is_stored_in_grams(self):
        self.assertIn("in grams", self.text)

    def test_olive_oil_shows_the_shape_the_rule_asks_for(self):
        data, _body = parse_frontmatter(read(VAULT / "nodes" / "food" / "Olive oil.md"))
        self.assertEqual(data["label_basis"], "100g")
        self.assertEqual(data["density_g_per_ml"], "0.91")
        self.assertEqual(data["density_source"], "database")
        expected = round_food_value(float(data["density_g_per_ml"]) * METRIC_TABLESPOON_ML)
        self.assertEqual(data["servings"], [f"1 tbsp = {expected} g"])

    def test_the_olive_oil_tablespoon_is_a_metric_15_ml_spoon(self):
        """A `tbsp` is 15 ml, never 10 ml: 15 x 0.91 = 13.65, one decimal 13.7 g."""
        data, body = parse_frontmatter(read(VAULT / "nodes" / "food" / "Olive oil.md"))
        expected = round_food_value(float(data["density_g_per_ml"]) * METRIC_TABLESPOON_ML)
        self.assertEqual(data["servings"][0], f"1 tbsp = {expected} g")
        self.assertNotIn("1 tbsp = 10 ml", body)
        self.assertIn(f"{METRIC_TABLESPOON_ML} ml", body)


class CreateFoodNeverOverwritesAMealTest(RoutineTextTestCase):
    """Spec #22 alias resolution: a Food and a Meal can share an alias, so a
    resolution hit is not always a Food. A new label may overwrite an existing
    Food; a Meal hit is not an existing Food and is never overwritten. Only the
    routine text can hold this, because the lint never sees the chosen node.
    """

    def setUp(self):
        self.text = read(CREATE_FOOD)

    def test_only_a_food_hit_is_overwritten(self):
        rule = self.one_line_with(self.text, "overwrites it")
        self.assertIn("A Food hit", rule)
        self.assertNotIn("A hit:", rule)

    def test_a_meal_hit_is_never_overwritten(self):
        rule = self.one_line_with(self.text, "never overwrite a Meal")
        self.assertIn("A Meal hit is not a Food", rule)

    def test_the_rule_sits_in_the_resolve_step(self):
        step = self.one_line_with(self.text, "never overwrite a Meal")
        self.assertIn("Resolve:", step)


class PantryOkTouchesNoFoodTest(unittest.TestCase):
    """The function that applies the pantry additions never touches a Food. The
    "ok" that marks a Food reviewed is the separate `mark_reviewed`."""

    PANTRY_DATA = {
        "type": "pantry",
        "name": "Pantry",
        "updated": "2026-09-14",
        "staples": ["[[Rice]]"],
        "items": ["[[Skyr]] = 1000 g"],
    }
    FOOD = {"type": "food", "name": "Chicken breast", "reviewed": "false"}

    def test_apply_restock_leaves_reviewed_out_of_the_pantry(self):
        result, _notes = apply_restock(self.PANTRY_DATA, [("Chicken breast", "1000 g", None)], "2026-09-15")
        self.assertNotIn("reviewed", result)

    def test_apply_restock_does_not_change_the_food_it_adds(self):
        food = dict(self.FOOD)
        apply_restock(self.PANTRY_DATA, [("Chicken breast", "1000 g", None)], "2026-09-15")
        self.assertEqual(food, self.FOOD)
        self.assertEqual(food["reviewed"], "false")

    def test_apply_pantry_change_leaves_reviewed_out(self):
        result = apply_pantry_change(self.PANTRY_DATA, ("bought", "Chicken breast", "1000 g", None), "2026-09-15")
        self.assertNotIn("reviewed", result)

    def test_mark_reviewed_is_the_separate_food_ok(self):
        self.assertEqual(mark_reviewed(self.FOOD)["reviewed"], "true")
        self.assertEqual(self.FOOD["reviewed"], "false")


class SpecNameCaseTest(unittest.TestCase):
    """Spec issue #22 writes "title case" for the Food file name, but every node
    in the repo is sentence case (`Chicken breast`, `Soy milk Alpro`). The
    specification document uses one term, "sentence case", and says in one place
    that #22 needs an owner correction. These tests keep that text from drifting
    back to two terms for one rule.
    """

    def setUp(self):
        self.text = NODES_SPEC.read_text(encoding="utf-8")

    def test_the_spec_names_the_convention_sentence_case(self):
        self.assertIn("sentence case", self.text)

    def test_the_file_name_rule_uses_the_term_and_shows_both_examples(self):
        hits = [line for line in self.text.split("\n") if "File name" in line]
        self.assertEqual(len(hits), 1, hits)
        rule = hits[0]
        self.assertIn("sentence case", rule)
        self.assertIn("`Chicken breast.md`", rule)
        self.assertIn("`Soy milk Alpro.md`", rule)

    def test_title_case_appears_only_in_the_issue_22_callout(self):
        hits = [line for line in self.text.split("\n") if "title case" in line.lower()]
        self.assertEqual(len(hits), 1, hits)
        callout = hits[0]
        self.assertIn("#22", callout)
        self.assertIn("owner", callout.lower())

    def test_the_repo_node_names_match_the_sentence_case_rule(self):
        for path in sorted((VAULT / "nodes" / "food").glob("*.md")):
            words = path.stem.split(" ")
            self.assertTrue(words[0][:1].isupper(), path.name)
            self.assertEqual(words[0], words[0][:1] + words[0][1:].lower(), path.name)


class SpecAliasStagePrecedenceTest(unittest.TestCase):
    """The Food-versus-Meal ask covers one stage. Spec #22 states the stage
    order and the collision rule side by side without saying which wins when a
    Food name and a Meal alias are the same word, so the specification document
    has to say it. `resolve_name()` stops at the first stage that matches.
    """

    def setUp(self):
        self.text = NODES_SPEC.read_text(encoding="utf-8")

    def test_the_spec_says_the_first_matching_stage_stops_the_search(self):
        hits = [line for line in self.text.split("\n") if "stops the search" in line]
        self.assertEqual(len(hits), 1, hits)
        rule = hits[0]
        self.assertIn("exact", rule)
        self.assertIn("asks nothing", rule)

    def test_the_ask_is_scoped_to_one_stage(self):
        hits = [line for line in self.text.split("\n") if "always ask" in line]
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("same stage", hits[0])


if __name__ == "__main__":
    unittest.main()

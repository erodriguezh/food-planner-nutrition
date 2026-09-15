"""The Meal and Day sections of docs/spec/nodes.md and the glossary match the lint and the routines (#25).

Run: python3 -m unittest discover lint
"""
import unittest
from pathlib import Path

from vault_lint import DAY_REQUIRED, MEAL_REQUIRED

VAULT = Path(__file__).resolve().parent.parent
NODES_SPEC = VAULT / "docs" / "spec" / "nodes.md"
GLOSSARY = VAULT / "CONTEXT.md"
USUAL_BREAKFAST = VAULT / "nodes" / "meal" / "Usual breakfast.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SpecMealDayTest(unittest.TestCase):
    """The Meal and Day sections of docs/spec/nodes.md match the lint schema."""

    def setUp(self):
        self.text = read(NODES_SPEC)
        self.meal = self.text.split("\n## Meal\n", 1)[1].split("\n## Day\n", 1)[0]
        self.day = self.text.split("\n## Day\n", 1)[1]

    def one_line_with(self, text: str, needle: str) -> str:
        hits = [line for line in text.split("\n") if needle in line]
        self.assertEqual(len(hits), 1, f"expected exactly one line with {needle!r}, found {len(hits)}")
        return hits[0]

    def test_the_placeholder_is_gone(self):
        self.assertNotIn("## Meal, Day", self.text)

    def test_every_required_meal_property_is_in_the_meal_table(self):
        for key in MEAL_REQUIRED:
            self.assertIn(f"`{key}`", self.meal, key)
        for key in ("`aliases`", "`slots`", "`cooked_weight_g`"):
            self.assertIn(key, self.meal)

    def test_every_required_day_property_is_in_the_day_table(self):
        for key in DAY_REQUIRED:
            self.assertIn(f"`{key}`", self.day, key)

    def test_the_entry_line_shapes_are_in_the_day_section(self):
        for shape in ("- [[<Meal or Food>]] = <amount> —", "- ~ [[", ", [[<Food>]] = <n> g"):
            self.assertIn(shape, self.day)

    def test_the_mark_rules_are_stated_for_line_meal_and_day(self):
        self.assertIn("`estimated`", self.meal)
        self.assertIn("right after the bullet", self.day)

    def test_the_meal_example_is_the_real_node(self):
        """Feedback item 7: the section says the example is the real node, so the
        two are compared character by character and the prototype amounts cannot
        come back through the spec."""
        example = self.meal.split("### Example\n", 1)[1].split("```", 2)[1]
        self.assertEqual(example.strip(), read(USUAL_BREAKFAST).strip())
        self.assertIn("The example is the real node `nodes/meal/Usual breakfast.md`", self.meal)

    def test_the_day_example_uses_the_real_meal_totals(self):
        """The Day example logs one portion of that same Meal, so its line and
        the running totals follow the node, not the prototype."""
        self.assertIn("- [[Usual breakfast]] = 1 portion \u2014 540 kcal \u00b7 46 P \u00b7 7 F \u00b7 67 C", self.day)
        self.assertNotIn("428", self.text)

    def test_the_stale_meal_rule_is_stated(self):
        rule = self.one_line_with(self.meal, "stale")
        self.assertIn("`source_date`", rule)
        self.assertIn("`totals_date`", rule)
        self.assertIn("`routines/log.md`", rule)

    def test_the_cooked_weight_conversion_is_stated(self):
        rule = self.one_line_with(self.meal, "cooked grams")
        self.assertIn("`cooked_weight_g`", rule)
        self.assertIn("`weight_g`", rule)
        self.assertIn("shrink", rule)
        self.assertIn("`~`", rule)

    def test_the_pantry_question_is_stated_once_in_the_day_lifecycle(self):
        """The rule belongs where logging is specified. The Pantry section keeps
        the short "Logging never changes the Pantry.", so the spec states the one
        question once."""
        rule = self.one_line_with(self.text, "was that the last of X?")
        self.assertIn("never changes the Pantry", rule)
        self.assertIn(rule, self.day)

    def test_the_slot_rule_and_the_index_month_line_are_stated(self):
        self.assertIn("next slot in order", self.day)
        self.assertIn("`- <YYYY-MM> | nodes/day/<YYYY-MM>/`", self.day)


class GlossaryTest(unittest.TestCase):
    def test_the_new_terms_are_defined_once(self):
        glossary = read(GLOSSARY)
        for term in ("**Slot word**", "**Guessed amount**", "**Estimation mark**", "**Entry line**", "**Month line**"):
            self.assertEqual(glossary.count(term), 1, term)

    def test_the_pantry_amount_states_the_one_log_question(self):
        """Story 59 lives in one glossary line: a log leaves the amount alone and
        asks about the last of a Food instead of writing the Pantry."""
        glossary = read(GLOSSARY)
        amount = [line for line in glossary.split("\n") if line.startswith("- **Amount**")]
        self.assertEqual(len(amount), 1)
        self.assertIn("Logging never changes it", amount[0])
        self.assertIn("was that the last of X?", amount[0])



if __name__ == "__main__":
    unittest.main()

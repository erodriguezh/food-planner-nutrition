"""The Meal and Day sections of docs/spec/nodes.md and the glossary match the lint and the routines (#25).

Run: python3 -m unittest discover lint
"""
import unittest
from pathlib import Path

from vault_lint import DAY_REQUIRED, MEAL_REQUIRED

VAULT = Path(__file__).resolve().parent.parent
NODES_SPEC = VAULT / "docs" / "spec" / "nodes.md"
GLOSSARY = VAULT / "CONTEXT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SpecMealDayTest(unittest.TestCase):
    """The Meal and Day sections of docs/spec/nodes.md match the lint schema."""

    def setUp(self):
        self.text = read(NODES_SPEC)
        self.meal = self.text.split("\n## Meal\n", 1)[1].split("\n## Day\n", 1)[0]
        self.day = self.text.split("\n## Day\n", 1)[1]

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

    def test_the_slot_rule_and_the_index_month_line_are_stated(self):
        self.assertIn("next slot in order", self.day)
        self.assertIn("`- <YYYY-MM> | nodes/day/<YYYY-MM>/`", self.day)


class GlossaryTest(unittest.TestCase):
    def test_the_new_terms_are_defined_once(self):
        glossary = read(GLOSSARY)
        for term in ("**Slot word**", "**Guessed amount**", "**Estimation mark**", "**Entry line**", "**Month line**"):
            self.assertEqual(glossary.count(term), 1, term)



if __name__ == "__main__":
    unittest.main()

"""Contract tests for the log, rebalance and create-meal routine texts (#25).

The routine files are what the agent reads at runtime, so the rules the lint
cannot see (which path the agent takes, what it asks, what it writes to the
chat) live in their text. These tests read the text and the routine functions
together, so the two cannot drift apart.

Run: python3 -m unittest discover lint
"""
import re
import unittest
from pathlib import Path

from vault_lint import (
    ROUTINE_SECTIONS,
    ROUTINE_TOKEN_LIMIT,
    estimate_tokens,
    parse_entry_line,
)

VAULT = Path(__file__).resolve().parent.parent
LOG = VAULT / "routines" / "log.md"
REBALANCE = VAULT / "routines" / "rebalance.md"
CREATE_MEAL = VAULT / "routines" / "create-meal.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RoutineTextTestCase(unittest.TestCase):
    def one_line_with(self, text: str, needle: str) -> str:
        hits = [line for line in text.split("\n") if needle in line]
        self.assertEqual(len(hits), 1, f"expected exactly one line with {needle!r}, found {len(hits)}")
        return hits[0]

    def step(self, text: str, number: int) -> str:
        return self.one_line_with(text, f"{number}. ")


class ShapeTest(unittest.TestCase):
    def test_the_three_routines_keep_the_five_sections_and_the_budget(self):
        for path in (LOG, REBALANCE, CREATE_MEAL):
            text = read(path)
            headings = [line[3:].strip() for line in text.split("\n") if line.startswith("## ")]
            self.assertEqual(headings, list(ROUTINE_SECTIONS), path.name)
            self.assertLess(estimate_tokens(text), ROUTINE_TOKEN_LIMIT, path.name)

    def test_the_router_points_at_all_three(self):
        router = read(VAULT / "ROUTER.md")
        for name in ("log", "rebalance", "create-meal"):
            self.assertIn(f"routines/{name}.md", router)


class LogRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(LOG)

    def test_the_routine_starts_with_its_title(self):
        """Every routine opens with `# <name>` and a blank line, so a reader of
        the file alone knows which routine it is."""
        self.assertTrue(self.text.startswith("# log\n\n"), self.text[:20])

    def test_a_log_adds_changes_or_removes_a_line(self):
        """Story 52. One routine covers the three edits of a Day line, so a step
        says so; the When examples alone only hint at it."""
        steps = self.text.split("## Steps\n", 1)[1].split("## Write", 1)[0]
        rule = self.one_line_with(steps.lower(), "add, change or remove a line")
        self.assertRegex(rule, r"^[56]\. ")

    def test_the_first_log_creates_the_day_the_state_and_the_month_line_in_one_commit(self):
        write = self.text.split("## Write\n", 1)[1].split("## Reply", 1)[0]
        for needle in ("`status: open`", '`goal: "[[Goals]]"`', "`open_day`", "month line", "`log: <date> <slot> <name> <amount>`"):
            self.assertIn(needle, write)
        self.assertEqual(write.count("commit"), 1)

    def test_the_line_shape_in_the_routine_parses(self):
        shape = self.one_line_with(self.text, "kcal · <P> P")
        example = re.search(r"`(- \[\[Name\]\].*?C)`", shape).group(1)
        line = (example.replace("[[Name]]", "[[Rice]]").replace("<n> g", "150 g")
                .replace("<kcal>", "528").replace("<P>", "11").replace("<F>", "1").replace("<C>", "117"))
        entry = parse_entry_line(line)
        self.assertEqual((entry.name, entry.amount, entry.unit), ("Rice", 150.0, "g"))

    def test_the_ingredient_change_form_stays_on_the_line(self):
        rule = self.one_line_with(self.text, "changed ingredient")
        self.assertIn("`, [[Food]] = <n> g`", rule)
        self.assertIn("not on the Meal", rule)

    def test_the_slot_rule_is_word_then_clock_then_next_in_order(self):
        """The slot rule lives in this line only. The owner settled the fixed
        order on PR #31, so the line names the four slots in that order and
        sends a filled slot to the next one, not to the clock's own slot."""
        rule = self.one_line_with(self.text, "Slot:")
        self.assertLess(rule.index("word"), rule.index("clock"))
        self.assertLess(rule.index("clock"), rule.index("next in order"))
        for boundary in ("11", "15", "18"):
            self.assertIn(boundary, rule)
        order = [rule.index(slot) for slot in ("breakfast", "lunch", "snack", "dinner")]
        self.assertEqual(order, sorted(order), rule)
        self.assertIn("filled earlier: next in order", rule)

    def test_a_slot_word_makes_the_meal_win(self):
        rule = self.one_line_with(self.text, "slot word")
        self.assertIn("Meal wins", rule)
        self.assertIn("ask", rule)

    def test_an_unknown_food_is_created_first_with_its_own_commit(self):
        rule = self.one_line_with(self.text, "new Food")
        self.assertIn("`routines/create-food.md`", rule)
        self.assertIn("own commit", rule)
        self.assertIn("then log", rule)

    def test_the_mark_sits_after_the_bullet_for_an_estimate_or_a_guess(self):
        rule = self.one_line_with(self.text, "`- ~ `")
        self.assertIn("after the bullet", rule)
        self.assertIn("estimate", rule)
        self.assertIn("guess", rule)

    def test_add_change_and_remove_are_one_routine(self):
        """Story 52. The three When examples are what routes an edit and a
        removal into this routine; the token budget keeps them and nothing else."""
        when = self.text.split("## When\n", 1)[1].split("\n\n", 1)[0]
        for phrase in ('"it was 200 g"', '"remove the snack"', '"yesterday I had'):
            self.assertIn(phrase, when)

    def test_a_past_date_writes_into_its_day_and_a_closed_day_is_refreshed(self):
        """A log into a closed Day rebuilds the Summary that close-day wrote and
        leaves the status alone (story 54, owner feedback 6 on PR #31). PR #32
        review 2: the Summary algorithm is not repeated here, so step 1 names
        the refresh mode of `routines/close-day.md` and the agent follows it."""
        rule = self.step(self.text, 1)
        self.assertIn("past date: its Day", rule)
        self.assertIn("closed Day: `routines/close-day.md` refresh, say so", rule)

    def test_one_fuzzy_hit_is_used_and_named(self):
        rule = self.step(self.text, 2)
        self.assertIn("fuzzy hit is used and named", rule)

    def test_the_rounding_rule_is_stated_here_once(self):
        rule = self.one_line_with(self.text, "half up")
        self.assertIn("whole", rule)
        self.assertIn("one decimal", rule)
        self.assertTrue(rule.startswith("4."), rule)
        # Half up covers both values: the lint compares against the rounded
        # number exactly, so "half up" may not read as the whole numbers only.
        self.assertLess(rule.index("whole"), rule.index("one decimal"), rule)
        self.assertLess(rule.index("one decimal"), rule.index("half up"), rule)
        # create-meal points here instead of repeating the rule.
        self.assertNotIn("half up", read(CREATE_MEAL))
        self.assertIn("`routines/log.md` step 4", read(CREATE_MEAL))

    def test_totals_and_estimated_are_rewritten_and_the_pantry_is_never_touched(self):
        """The Day's own totals and its `estimated` checkbox. Step 4 names the
        Meal's seven totals, so this line says whose totals it rewrites."""
        rule = self.one_line_with(self.text, "Rewrite Day totals")
        self.assertIn("`estimated`", rule)
        self.assertIn("never the Pantry", rule)
        self.assertIn("`routines/rebalance.md`", self.text.split("## Reply\n", 1)[1])

    def test_a_stale_meal_is_recomputed_before_it_is_logged(self):
        """Story 32 and owner feedback 4 on PR #31, round 3: the daily agent
        reads this file and not `docs/spec/nodes.md`, so the line states the
        mutation. An ingredient Food with a `source_date` after the Meal's
        `totals_date` makes the stored totals stale; the routine sums the
        ingredient Foods again and writes the Meal's seven totals, `totals_date`
        and `estimated` before the Day entry of step 5."""
        rule = self.one_line_with(self.text, "`totals_date`")
        self.assertRegex(rule, r"^4\. ")
        self.assertIn("`source_date`", rule)
        self.assertLess(rule.index("`source_date`"), rule.index("`totals_date`"), rule)
        self.assertIn("sum its Foods", rule)  # the totals are summed from the ingredients
        # The Meal node is written, not recomputed in memory: the verb `write` on
        # its own, not the tail of `rewrite`, and the Meal named as its target.
        match = re.search(r"\bwrite the Meal's\b(.*)$", rule)
        self.assertIsNotNone(match, rule)
        written = match.group(1)
        for field in ("seven totals", "`totals_date`", "`estimated`"):
            self.assertIn(field, written)
        # The Meal is written first, before the Day entry of step 5.
        self.assertIn("first", written)
        self.assertRegex(self.one_line_with(self.text, "kcal \u00b7 <P> P"), r"^5\. ")

    def test_cooked_grams_convert_through_the_cooked_weight(self):
        """Stories 37 and 38: a leftover weighed cooked converts to the canonical
        grams of the Meal; without a cooked weight the shrink is a guess, so the
        error is stated and the entry carries the mark."""
        rule = self.one_line_with(self.text, "`cooked_weight_g`")
        self.assertIn("cooked g", rule)
        self.assertIn("`weight_g`", rule)
        self.assertIn("guess shrink", rule)
        self.assertIn("say the error", rule)
        self.assertIn("`~`", rule)

    def test_more_than_the_pantry_holds_asks_one_question(self):
        """Story 59: the one Pantry question of the log routine. The log still
        writes nothing to the Pantry, so both halves sit on the same line."""
        rule = self.one_line_with(self.text, "was that the last of X?")
        self.assertIn("never the Pantry", rule)

    def test_the_reply_names_the_slot_and_points_at_rebalance(self):
        """The reply of a log is the rebalance reply plus the slot and the mark.
        The token budget of this file keeps only the two the pointer does not
        carry; `RebalanceRoutineTest` pins the one line and what is left."""
        reply = self.text.split("## Reply\n", 1)[1]
        self.assertIn("`routines/rebalance.md`", reply)
        self.assertIn("slot", reply)
        self.assertIn("`~`", reply)


class RebalanceRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(REBALANCE)

    def test_remaining_is_target_minus_running_totals_after_every_log(self):
        rule = self.one_line_with(self.text, "Remaining =")
        self.assertIn("target minus running totals", rule)
        self.assertIn("after every log", rule)
        self.assertIn("over its max", rule)

    def test_open_slots_are_the_empty_ones_in_the_fixed_order(self):
        """The open-slot list is the fixed order minus the filled and the
        removed slots; a removed slot is chat only and writes nothing."""
        rule = self.one_line_with(self.text, "Open slots:")
        self.assertIn("no entry yet", rule)
        order = [rule.index(slot) for slot in ("breakfast", "lunch", "snack", "dinner")]
        self.assertEqual(order, sorted(order), rule)
        self.assertIn("minus slots removed in chat", rule)

    def test_a_suggestion_comes_only_on_request(self):
        rule = self.one_line_with(self.text, "only on request")
        self.assertIn('"Plan today"', rule)
        self.assertIn("every open slot in full", rule)
        self.assertIn("next slot in full", rule)
        self.assertIn("one rough line", rule)

    def test_pantry_only_in_the_picking_order_with_expiring_items_first(self):
        rule = self.one_line_with(self.text, "Pantry only")
        order = [rule.index(word) for word in ("protein", "grain", "vegetable", "fruit", "fat")]
        self.assertEqual(order, sorted(order), rule)
        self.assertIn("`until` today or tomorrow first", rule)
        self.assertIn("10 g", rule)

    def test_removed_slots_write_nothing_and_the_routine_writes_nothing(self):
        self.assertIn('"no snack today" writes nothing', self.text)
        write = self.text.split("## Write\n", 1)[1].split("## Reply", 1)[0]
        self.assertTrue(write.strip().startswith("Nothing"), write)

    def test_the_reply_after_a_log_is_one_line_with_what_is_left(self):
        """`routines/log.md` points its Reply here, so the one line and what is
        left are stated once, in this file."""
        reply = self.text.split("## Reply\n", 1)[1]
        self.assertIn("After a log: one line, what is left", reply)

    def test_the_evening_question_and_the_mark(self):
        rule = self.one_line_with(self.text, "did you skip lunch?")
        self.assertIn("`~`", rule)


class CreateMealRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(CREATE_MEAL)

    def test_exactly_one_ok_question(self):
        self.assertEqual(len(re.findall(r"ok\?", self.text)), 2)  # the step and the reply
        steps = self.text.split("## Steps\n", 1)[1].split("## Write", 1)[0]
        self.assertEqual(len(re.findall(r"ok\?", steps)), 1)

    def test_the_ok_sets_reviewed_and_a_correction_is_written_instead(self):
        steps = self.text.split("## Steps\n", 1)[1].split("## Write", 1)[0]
        rule = self.one_line_with(steps, '"ok?"')
        self.assertIn("`reviewed: true`", rule)
        self.assertIn("correction", rule)

    def test_unknown_foods_are_auto_created_with_one_summary_line(self):
        rule = self.one_line_with(self.text, "Unknown Foods")
        self.assertIn("`routines/create-food.md`", rule)
        self.assertIn("`reviewed: false`", rule)
        self.assertIn("one commit each", rule)
        self.assertIn("one summary line", rule)

    def test_the_name_must_be_free(self):
        rule = self.step(self.text, 1)
        self.assertIn("free of every Food and Meal name", rule)
        self.assertIn("ask", rule)

    def test_the_totals_come_from_the_food_nodes_with_the_estimate_mark(self):
        rule = self.one_line_with(self.text, "Sum the Food nodes")
        for key in ("`weight_g`", "`totals_date`", "`portions`", "`slots`", "`aliases`", "`estimated`", "`cooked_weight_g`"):
            self.assertIn(key, rule)

    def test_the_day_lines_stay_as_eaten(self):
        self.assertIn("Day lines stay as eaten", self.text)

    def test_the_write_has_the_index_line_shape_and_the_commit(self):
        write = self.text.split("## Write\n", 1)[1].split("## Reply", 1)[0]
        self.assertIn("`- [[Name]] | <slots or any> | <aliases>`", write)
        self.assertIn("`create-meal: <name>`", write)
        self.assertIn("`state.md`", write)  # ROUTER hard rule 5
        self.assertLess(write.index("New Foods first"), write.index("Meal"))



if __name__ == "__main__":
    unittest.main()

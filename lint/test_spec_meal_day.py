"""The Meal and Day sections of docs/spec/nodes.md and the glossary match the lint and the routines (#25).

Run: python3 -m unittest discover lint
"""
import unittest
from pathlib import Path

from vault_lint import (
    DAY_REQUIRED,
    MEAL_REQUIRED,
    SUMMARY_BULLET_RE,
    SUMMARY_GOAL_RE,
    SUMMARY_HINT_PREFIX,
    SUMMARY_MACROS,
    SUMMARY_SEPARATOR,
    SUMMARY_TABLE_HEADER,
    SUMMARY_VERDICT_RE,
)

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
        for prototype in ("428 kcal", "kcal: 428", "weight_g: 500", "Soy milk Alpro]] = 150 g"):
            self.assertNotIn(prototype, self.text, prototype)

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

    def test_history_freezes_the_recorded_numbers_and_not_the_entry_shape(self):
        """PR #31 review: the closed-Day sentences say what history frees, so a
        reader cannot take them for "a closed Day is unchecked"."""
        rule = self.one_line_with(self.day, "never makes a malformed line valid")
        self.assertIn("closed or auto-closed Day", rule)
        self.assertIn("`check_entry_shape()`", self.day)

    def test_a_missing_changed_link_fails_on_every_day(self):
        """Decided with #26 after the PR #31 review: a changed link whose node does not
        exist fails on a closed Day as the entry's own link does. Both closed-Day
        sentences name the missing node next to the wrong type, as the lint does."""
        rule = self.one_line_with(self.day, "The lint fails a change on a Food entry")
        history = self.one_line_with(self.day, "never makes a malformed line valid")
        for sentence in (rule, history):
            self.assertIn("missing", sentence)
            self.assertIn("not a Food", sentence)
        self.assertIn("does not exist", history)

    def test_the_slot_rule_and_the_index_month_line_are_stated(self):
        self.assertIn("next slot in order", self.day)
        self.assertIn("`- <YYYY-MM> | nodes/day/<YYYY-MM>/`", self.day)

    # --- #26: the Summary, the verdict and the review ---------------------------------

    def test_close_day_exists_and_the_spec_no_longer_says_otherwise(self):
        self.assertTrue((VAULT / "routines" / "close-day.md").is_file())
        self.assertTrue((VAULT / "routines" / "review.md").is_file())
        self.assertNotIn("does not exist yet", self.text)

    def test_the_summary_section_states_the_fixed_order(self):
        summary = self.day.split("### Summary\n", 1)[1].split("\n### ", 1)[0]
        self.assertIn(f"`{SUMMARY_TABLE_HEADER}`", summary)
        self.assertIn("`| TOTAL | <kcal> | <P> | <F> | <C> |`", summary)
        self.assertIn("`Goal <kcal> kcal (<min>-<max>), <P> P (<min>-<max>), <F> F (<min>-<max>), <C> C (<min>-<max>).`", summary)
        self.assertIn("`- <macro> <n> over|under`", summary)
        self.assertIn("`Hint: <one line for tomorrow>`", summary)
        order = [summary.index(word) for word in ("slot table", "goal line", "Four bullets", "verdict in fixed words", "At most one line")]
        self.assertEqual(order, sorted(order))
        for macro in SUMMARY_MACROS:
            self.assertIn(f"`{macro}`", summary)

    def test_the_separator_row_of_the_summary_table_is_fixed(self):
        """PR #32 review round 3, item 4: the lint takes one separator row, so the
        spec names it and says it is the only one, instead of leaving the row to
        the reader."""
        rule = self.one_line_with(self.day, "separator row")
        self.assertIn(f"`{SUMMARY_SEPARATOR}`", rule)
        self.assertIn("five", rule)
        summary = self.day.split("### Summary\n", 1)[1].split("\n### ", 1)[0]
        example = summary.split("```\n", 2)[1]
        self.assertIn(f"{SUMMARY_TABLE_HEADER}\n{SUMMARY_SEPARATOR}\n", example)

    def test_the_summary_example_has_the_lint_shape(self):
        """The example is what close-day writes, so its lines pass the lint regexes."""
        summary = self.day.split("### Summary\n", 1)[1].split("\n### ", 1)[0]
        example = summary.split("```\n", 2)[1]
        lines = [line for line in example.split("\n") if line.strip() and not line.startswith("## ")]
        self.assertEqual(lines[0], SUMMARY_TABLE_HEADER)
        total = [i for i, line in enumerate(lines) if line.startswith("| TOTAL | ~")]
        self.assertEqual(len(total), 1, lines)
        goal = lines[total[0] + 1]
        bullets, verdict, hint = lines[total[0] + 2:total[0] + 6], lines[total[0] + 6], lines[total[0] + 7:]
        self.assertIsNotNone(SUMMARY_GOAL_RE.match(goal), goal)
        for macro, line in zip(SUMMARY_MACROS, bullets):
            self.assertRegex(line, SUMMARY_BULLET_RE)
            self.assertTrue(line.startswith(f"- {macro} "), line)
        self.assertIsNotNone(SUMMARY_VERDICT_RE.match(verdict), verdict)
        self.assertEqual(len(hint), 1, hint)
        self.assertTrue(hint[0].startswith(SUMMARY_HINT_PREFIX), hint)

    def test_the_bullet_shape_itself_rejects_zero_over(self):
        """Review item 7 on PR #32: `SUMMARY_BULLET_RE` is the bullet shape the spec
        example is read against, so the shape rejects `0 over` on its own, without
        the arithmetic of the bullet loop."""
        for line in ("- kcal 0 over", "- protein 0.0 over"):
            self.assertIsNone(SUMMARY_BULLET_RE.match(line), line)
        for line in ("- kcal 0 under", "- protein 66.5 under", "- carbs 106 over"):
            self.assertIsNotNone(SUMMARY_BULLET_RE.match(line), line)

    def test_the_goal_and_gap_number_grammar_and_the_exact_hit_are_stated(self):
        """Review items 5 and 7 on PR #32: a Goals target is a `number`, so the goal
        line and the gap of a bullet may carry a decimal, and a macro that hits its
        target exactly has one bullet, `- <macro> 0 under`."""
        rule = self.one_line_with(self.day, "`- <macro> 0 under`")
        self.assertIn("135.5", rule)
        self.assertIn("`0 over` fails", rule)
        self.assertIn("no sign", rule)
        self.assertIn("the table numbers stay whole", rule)

    def test_the_mark_and_the_goal_change_rules_are_stated_for_the_summary(self):
        rule = self.one_line_with(self.day, "a plain Day carries none")
        self.assertIn("exactly when the Day is estimated", rule)
        rule = self.one_line_with(self.day, "It records the targets")
        self.assertIn("goal change", rule)
        self.assertIn("today's Goals", rule)

    def test_the_verdict_is_stated_against_the_stored_bounds(self):
        """PR #32 review round 2, item 2: the bounds of the close are on the file
        now, so the spec says the verdict is judged against them and not against
        today's Goals."""
        rule = self.one_line_with(self.day, "A `high` macro is `over` in its bullet")
        self.assertIn("`on target`", rule)
        self.assertIn("`off target:`", rule)
        self.assertIn("range", rule)
        self.assertIn("column order", rule)
        self.assertNotIn("not the bounds", self.day)

    def test_the_verdict_names_each_macro_at_most_once(self):
        """PR #32 review round 2, item 4: the spec states the one-entry-per-macro
        rule the lint checks, because the weekly review counts these entries."""
        rule = self.one_line_with(self.day, "A `high` macro is `over` in its bullet")
        self.assertIn("at most once", rule)

    def test_the_goal_line_is_the_goals_snapshot_a_refresh_reuses(self):
        """PR #32 review round 2, item 2 and spec #22 story 13: an old closed Day
        keeps the goal comparison it used, so the refresh of a corrected Day
        reads the stored targets and bounds instead of today's Goals."""
        rule = self.one_line_with(self.day, "It records the targets and the ranges")
        self.assertIn("refresh", rule)
        self.assertIn("today's Goals", rule)
        self.assertIn("`<macro>_min`", rule)
        self.assertIn("`<macro>_max`", rule)

    def test_the_state_is_cleared_at_close(self):
        rule = self.one_line_with(self.day, "still names a closed or auto-closed Day")
        self.assertIn("`close-day: <date> <verdict>`", rule)

    def test_the_review_section_matches_the_routine(self):
        review = self.day.split("### Review\n", 1)[1].split("\n### ", 1)[0]
        for needle in ("`routines/review.md`", "Monday to Sunday", "writes nothing", "`closed` and `auto-closed` Days only",
                       "missing days", "auto-closed count", "open Day out with one line", "two lines", "`on target`",
                       "`<macro> low|high`", "`~`", "under ten lines"):
            self.assertIn(needle, review)

    def test_the_review_section_averages_all_seven_totals_and_fixes_the_mark(self):
        """PR #32 review round 3, item 2: spec #22 asks for "averages of the
        seven totals", so the Average line carries all seven while the Target
        line keeps the four Goals targets, and the estimation mark has one
        canonical position: `~` before every number of the Average line."""
        review = self.day.split("### Review\n", 1)[1].split("\n### ", 1)[0]
        for needle in ("seven totals", "four Goals targets", "`~` before every number"):
            self.assertIn(needle, review)
        # The three added labels are the Day node keys without `_g`.
        for label in ("fiber", "sugar", "salt"):
            self.assertIn(f"`{label}_g`", self.day)
        average = self.one_line_with(read(GLOSSARY), "- **Weekly average**")
        self.assertIn("seven totals", average)
        self.assertIn("`~` before every number", average)

    def test_the_review_section_fixes_the_tie_shape_of_the_most_common_miss(self):
        """PR #32 review round 4: the reply defined one miss only, so a tie left
        the punctuation and the order to the app. The spec states the one line:
        the tied misses `; ` apart in the macro order, `low` before `high`
        inside one macro, `none` when nothing missed, and never a second line.
        Issue #28 seeds an acceptance run that asserts the line."""
        review = self.day.split("### Review\n", 1)[1].split("\n### ", 1)[0]
        for needle in ("`; `", "`kcal`, `protein`, `fat`, `carbs`", "`low` before `high`",
                       "`Most common miss: none`", "second `Most common miss` line", "no rolling window"):
            self.assertIn(needle, review)
        miss = self.one_line_with(read(GLOSSARY), "- **Most common miss**")
        for needle in ("`; `", "`kcal`, `protein`, `fat`, `carbs`", "`low` before `high`"):
            self.assertIn(needle, miss)

    def test_the_review_section_states_the_eligible_dates_and_the_empty_week(self):
        """Review item 6 on PR #32: "this week" runs Monday to today, so the
        denominator is the eligible dates and a date still to come is never
        missing. A week with nothing counted has a fixed shape, so the average
        never divides by zero."""
        review = self.day.split("### Review\n", 1)[1].split("\n### ", 1)[0]
        for needle in ("eligible dates", "Monday to today", "never missing", "`Average: n/a`",
                       "`On target: 0 of 0`", "`Most common miss: none`"):
            self.assertIn(needle, review)
        self.assertNotIn("seven days", review)

    def test_a_log_into_a_closed_day_names_the_close_day_refresh(self):
        """Review item 2 on PR #32: the rebuild of a closed Day's Summary is the
        refresh mode of `routines/close-day.md`, and it rides on the `log:`
        commit instead of writing a `close-day:` one."""
        rule = self.one_line_with(self.day, "A log into a closed Day")
        self.assertIn("refresh", rule)
        self.assertIn("keeps the status", rule)
        self.assertIn("`log:", rule)
        # PR #32 review round 2, item 1: the totals are rewritten first, the
        # Summary is rebuilt from them afterwards.
        self.assertLess(rule.index("totals"), rule.index("refresh"))
        self.assertIn("then", rule)


class GlossaryTest(unittest.TestCase):
    def test_the_new_terms_are_defined_once(self):
        glossary = read(GLOSSARY)
        for term in ("**Slot word**", "**Guessed amount**", "**Estimation mark**", "**Entry line**", "**Month line**",
                     "**Macro bullet**", "**Hint**", "**Days on target**"):
            self.assertEqual(glossary.count(term), 1, term)

    def test_the_summary_and_verdict_terms_match_the_lint_words(self):
        """#26: the glossary is the ubiquitous language, so its Summary and Verdict
        lines carry the same fixed order and macro words the lint checks."""
        glossary = read(GLOSSARY)
        summary = [line for line in glossary.split("\n") if line.startswith("- **Summary**")][0]
        for part in ("slot table", "TOTAL row", "goal line", "range", "one bullet per macro", "verdict", "at most one hint", "rewrites it"):
            self.assertIn(part, summary)
        verdict = [line for line in glossary.split("\n") if line.startswith("- **Verdict**")][0]
        for macro in SUMMARY_MACROS:
            self.assertIn(f"`{macro}`", verdict)
        # PR #32 review round 2, item 4: one entry per off macro, in the column order.
        self.assertIn("at most once", verdict)
        self.assertIn("column order", verdict)
        self.assertIn("`- <macro> <n> over|under`", glossary)
        self.assertIn("`Hint: ...`", glossary)

    def test_the_days_covered_term_counts_the_eligible_dates(self):
        """Review item 6 on PR #32: the term said "the seven days", which made a
        date still to come a missing day of the current week."""
        glossary = read(GLOSSARY)
        line = [one for one in glossary.split("\n") if one.startswith("- **Days covered**")][0]
        self.assertIn("eligible", line)
        self.assertNotIn("seven", line)

    def test_the_macro_bullet_term_states_the_exact_hit_and_the_decimal_gap(self):
        """Review items 5 and 7 on PR #32: the glossary is the ubiquitous language, so
        the Macro bullet line carries the `0 under` rule and the decimal gap."""
        glossary = read(GLOSSARY)
        bullet = [line for line in glossary.split("\n") if line.startswith("- **Macro bullet**")][0]
        self.assertIn("`0 under`", bullet)
        self.assertIn("`0 over`", bullet)
        self.assertIn("decimal", bullet)
        self.assertIn("no sign", bullet)

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

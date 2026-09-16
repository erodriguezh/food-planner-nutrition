"""Contract tests for the close-day and review routine texts (#26).

The routine files are what the agent reads at runtime. The lint judges the
Summary a close leaves on disk; the rules it cannot see (the reply, the "ok"
step, the review lines, what a routine writes) live in the routine text. These
tests pin that text next to the lint constants, so the two cannot drift apart.

Run: python3 -m unittest discover lint
"""
import re
import unittest
from pathlib import Path

from vault_lint import (
    ROUTINE_SECTIONS,
    ROUTINE_TOKEN_LIMIT,
    SLOTS,
    SUMMARY_BULLET_RE,
    SUMMARY_GOAL_RE,
    SUMMARY_HINT_PREFIX,
    SUMMARY_MACROS,
    SUMMARY_TABLE_HEADER,
    SUMMARY_VERDICT_RE,
    estimate_tokens,
)

VAULT = Path(__file__).resolve().parent.parent
CLOSE_DAY = VAULT / "routines" / "close-day.md"
REVIEW = VAULT / "routines" / "review.md"
LOG = VAULT / "routines" / "log.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RoutineTextTestCase(unittest.TestCase):
    def one_line_with(self, text: str, needle: str) -> str:
        hits = [line for line in text.split("\n") if needle in line]
        self.assertEqual(len(hits), 1, f"expected exactly one line with {needle!r}, found {len(hits)}")
        return hits[0]

    def step(self, text: str, number: int) -> str:
        return self.one_line_with(text, f"{number}. ")

    def section(self, text: str, name: str) -> str:
        after = text.split(f"## {name}\n", 1)[1]
        return after.split("\n## ", 1)[0]


class ShapeTest(unittest.TestCase):
    def test_both_routines_keep_the_five_sections_and_the_budget(self):
        for path in (CLOSE_DAY, REVIEW):
            text = read(path)
            headings = [line[3:].strip() for line in text.split("\n") if line.startswith("## ")]
            self.assertEqual(headings, list(ROUTINE_SECTIONS), path.name)
            self.assertLess(estimate_tokens(text), ROUTINE_TOKEN_LIMIT, path.name)

    def test_both_routines_start_with_their_title(self):
        self.assertTrue(read(CLOSE_DAY).startswith("# close-day\n\n"))
        self.assertTrue(read(REVIEW).startswith("# review\n\n"))

    def test_the_router_points_at_both_and_they_exist(self):
        """ROUTER.md named the two files before they existed; now every routine
        the router names is a file."""
        router = read(VAULT / "ROUTER.md")
        for name in re.findall(r"`routines/([a-z-]+)\.md`", router):
            self.assertTrue((VAULT / "routines" / f"{name}.md").is_file(), name)
        self.assertIn("`routines/close-day.md`", router)
        self.assertIn("`routines/review.md`", router)


class CloseDayRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(CLOSE_DAY)
        self.steps = self.section(self.text, "Steps")

    def test_the_when_covers_the_request_and_the_auto_close(self):
        when = self.section(self.text, "When")
        self.assertIn('"close the day"', when)
        self.assertIn("auto-close", when)

    def test_the_auto_close_path_sets_its_status_before_the_new_day(self):
        """Acceptance #26: a log dated after the open Day writes that Day's
        Summary with `status: auto-closed` before it creates the new Day."""
        rule = self.step(self.steps, 1)
        self.assertIn("`status: auto-closed`", rule)
        self.assertIn("before the new Day exists", rule)
        self.assertIn("none: say so, stop", rule)

    def test_the_table_step_matches_the_lint_header_and_the_total_row(self):
        rule = self.step(self.steps, 2)
        self.assertIn(f"`{SUMMARY_TABLE_HEADER}`", rule)
        self.assertIn("`| TOTAL | ... |`", rule)
        self.assertIn("one row per slot with an entry, in order", rule)
        self.assertIn("Day totals", rule)

    def test_the_mark_goes_on_every_table_number_of_an_estimated_day(self):
        rule = self.step(self.steps, 2)
        self.assertIn("`estimated: true`", rule)
        self.assertIn("`~` before every table number", rule)

    def test_the_goal_line_shape_parses(self):
        rule = self.step(self.steps, 3)
        shape = re.search(r"`(Goal .*?C\.)`", rule).group(1)
        line = shape.replace("<kcal>", "2500").replace("<P>", "135").replace("<F>", "60").replace("<C>", "355")
        self.assertIsNotNone(SUMMARY_GOAL_RE.match(line), line)
        self.assertIn("Goals targets", rule)

    def test_the_four_bullets_name_the_lint_macro_words_in_order(self):
        rule = self.step(self.steps, 4)
        self.assertIn("Four bullets", rule)
        self.assertIn("`- <kcal|protein|fat|carbs> <n> over|under`", rule)
        self.assertIn("in that order", rule)
        self.assertIn("no sign", rule)
        for macro in SUMMARY_MACROS:
            self.assertIsNotNone(SUMMARY_BULLET_RE.match(f"- {macro} 12 under"), macro)

    def test_the_verdict_words_are_the_fixed_ones(self):
        """Acceptance #26: `on target` when all four macros sit inside the stored
        bounds, else `off target:` with each off macro and its direction."""
        rule = self.step(self.steps, 5)
        self.assertIn("`on target`", rule)
        self.assertIn("inside min and max", rule)
        self.assertIn("`off target: <macro> low|high`", rule)
        self.assertIn("one per off macro", rule)
        self.assertIsNotNone(SUMMARY_VERDICT_RE.match("off target: protein low, fat high"))

    def test_the_hint_is_one_optional_last_line(self):
        rule = self.step(self.steps, 6)
        self.assertIn(f"`{SUMMARY_HINT_PREFIX}<one line for tomorrow>`", rule)
        self.assertIn("Last line", rule)
        self.assertIn("only when useful", rule)

    def test_unreviewed_foods_are_named_and_one_ok_reviews_them_all(self):
        """Acceptance #26: the reply ends with one line naming unreviewed Foods
        eaten today; "ok" reviews them all."""
        rule = self.step(self.steps, 7)
        self.assertIn("unreviewed Foods eaten today", rule)
        self.assertIn('"ok": `reviewed: true` on all', rule)
        self.assertIn("commit `close-day: reviewed <names>`", rule)

    def test_the_write_closes_clears_and_commits_in_one_step(self):
        """Acceptance #26: the Summary, `status: closed`, the cleared State and
        the commit are one step."""
        write = self.section(self.text, "Write")
        for needle in ("`## Summary`", "`status: closed`", "`state.md`", '`open_day: ""`', "`updated`", "`close-day: <date> <verdict>`"):
            self.assertIn(needle, write)
        self.assertEqual(write.count("commit"), 1)

    def test_the_reply_has_the_table_the_verdict_the_hint_and_the_unreviewed_line(self):
        reply = self.section(self.text, "Reply")
        for needle in ("Table", "verdict", "hint", "one line naming the unreviewed Foods", "none: no line", "`~` on every total when estimated"):
            self.assertIn(needle, reply)

    def test_a_log_into_a_closed_day_is_the_log_routines_job(self):
        """The rewrite of a closed Day's Summary is stated once, in `routines/log.md`
        step 1; close-day does not repeat it."""
        self.assertIn("closed Day: rewrite Summary, keep status, say so", read(LOG))
        self.assertNotIn("keep status", self.text)


class ReviewRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(REVIEW)
        self.steps = self.section(self.text, "Steps")

    def test_the_when_has_the_three_meanings(self):
        when = self.section(self.text, "When")
        for phrase in ('"how was my week"', '"last week"', '"review"'):
            self.assertIn(phrase, when)

    def test_the_week_is_monday_to_sunday_with_no_rolling_window(self):
        rule = self.step(self.steps, 1)
        self.assertIn("Monday to Sunday", rule)
        self.assertIn("current week so far", rule)
        self.assertIn('"last week": the previous week', rule)
        self.assertIn("No rolling window", rule)

    def test_only_closed_days_count_and_the_open_day_gets_one_line(self):
        rule = self.step(self.steps, 2)
        self.assertIn("`status: closed` and `auto-closed` Days only", rule)
        self.assertIn("Today open: leave it out, say so in one line", rule)
        self.assertIn("Missing days: state them, never guess", rule)

    def test_the_average_carries_the_mark_when_any_counted_day_is_estimated(self):
        rule = self.step(self.steps, 3)
        self.assertIn("Average per day", rule)
        # The rounding rule is stated once, in log.md step 4; this routine points there.
        self.assertIn("`routines/log.md` step 4", rule)
        self.assertNotIn("half up", self.text)
        self.assertIn("`~` on the average when any counted Day is `estimated: true`", rule)

    def test_days_on_target_and_the_most_common_miss_come_from_the_verdicts(self):
        rule = self.one_line_with(self.steps, "4. Days on target")
        self.assertIn("verdict is `on target`", rule)
        self.assertIn("Most common miss", rule)
        self.assertIn("`<macro> low|high`", rule)
        self.assertIn("day count", rule)

    def test_the_review_writes_nothing(self):
        """Acceptance #26: the review writes nothing."""
        write = self.section(self.text, "Write")
        self.assertTrue(write.strip().startswith("Nothing"), write)
        self.assertIn("no commit", write)
        self.assertNotIn("state.md", self.text)

    def test_the_reply_is_the_fixed_lines_under_ten(self):
        """The four fixed review lines: days covered with the auto-closed count,
        the average against the target on two lines, days on target, the most
        common miss; plus the one line for an open today."""
        reply = self.section(self.text, "Reply")
        self.assertIn("Under ten lines", reply)
        fixed = [line for line in reply.split("\n") if line.startswith("`")]
        self.assertLess(len(fixed), 10)
        starts = [line.split(":")[0].lstrip("`") for line in fixed]
        self.assertEqual(starts[:5], ["Days", "Average", "Target", "On target", "Most common miss"])
        self.assertIn("auto-closed", fixed[0])
        self.assertIn("missing", fixed[0])
        self.assertIn("`Today is open and not counted.`", reply)
        for line in fixed[1:3]:
            self.assertIn("<kcal> kcal · <P> P · <F> F · <C> C", line)


class SlotOrderTest(unittest.TestCase):
    def test_the_lint_slot_order_is_the_one_the_routines_use(self):
        self.assertEqual(SLOTS, ("breakfast", "lunch", "snack", "dinner"))


if __name__ == "__main__":
    unittest.main()

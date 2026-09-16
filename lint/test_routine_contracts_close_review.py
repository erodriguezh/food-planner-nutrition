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

    def test_the_router_names_every_close_day_mode(self):
        """Code review of PR #32: the router line named the close and the
        auto-close, the two modes of the day the routine had then. The refresh
        is the third, so the line names it as the auto-close is named."""
        router = read(VAULT / "ROUTER.md")
        line = [one for one in router.split("\n") if "`routines/close-day.md`" in one]
        self.assertEqual(len(line), 1, line)
        for mode in ("closes the day", "auto-closes", "refresh"):
            self.assertIn(mode, line[0])

    def test_the_router_routes_the_bare_word_review(self):
        """PR #32 review 4: the router line read "asks about the week" only, so
        a bare "review" reached the review routine by guess. The line names the
        word and the week, and `routines/review.md` keeps both triggers."""
        router = read(VAULT / "ROUTER.md")
        line = [one for one in router.split("\n") if "`routines/review.md`" in one]
        self.assertEqual(len(line), 1, line)
        self.assertIn('says "review"', line[0])
        self.assertIn("week", line[0])
        self.assertIn('"review"', self.section_when(read(REVIEW)))

    def section_when(self, text: str) -> str:
        return text.split("## When\n", 1)[1].split("\n\n", 1)[0]


class CloseDayRoutineTest(RoutineTextTestCase):
    def setUp(self):
        self.text = read(CLOSE_DAY)
        self.steps = self.section(self.text, "Steps")

    def test_the_when_covers_the_request_and_the_auto_close(self):
        when = self.section(self.text, "When")
        self.assertIn('"close the day"', when)
        self.assertIn("auto-close", when)

    def test_the_read_names_the_foods_step_7_needs(self):
        """PR #32 review 3: `## Read` said "The open Day, Goals." while step 7
        needs the `reviewed` flag of the Foods eaten that day, which a logged
        Meal only reaches through its own Foods. The Read section names both,
        and the Day covers the open one and the older one of an auto-close."""
        read_section = self.section(self.text, "Read").strip()
        self.assertTrue(read_section.startswith("The Day, Goals"), read_section)
        self.assertIn("`reviewed`", read_section)
        self.assertIn("Foods", read_section)
        self.assertIn("Meals", read_section)
        # One short line: the vault opens as few files as it can.
        self.assertEqual(len(read_section.split("\n")), 1, read_section)

    def test_the_step_that_picks_the_day_reaches_every_mode(self):
        """Code review of PR #32 item 2: a refresh runs on a closed Day with no
        open Day, so step 1 has to name the Day of that mode as well, or the
        agent stops at step 1 and never rebuilds the Summary. The When line
        carries the trigger of every mode the Write section writes."""
        rule = self.step(self.steps, 1)
        self.assertIn("none: say so, stop", rule)
        self.assertIn("refresh", rule)
        when = self.section(self.text, "When")
        for mode in ("auto-close", "refresh"):
            self.assertIn(mode, when)

    def test_the_write_names_one_status_per_close_mode_and_none_on_its_own(self):
        """PR #32 review 1: step 1 wrote `status: auto-closed` while `## Write`
        said `status: closed` for every close, so the file contradicted itself.
        The statuses live in `## Write`, each in the clause of its own mode, and
        no clause anywhere in the file names a status without its mode."""
        write = self.section(self.text, "Write")
        clauses = [clause.strip() for clause in re.split(r"[.;]", write) if "`status:" in clause]
        by_status = {re.search(r"`status: (auto-closed|closed)`", clause).group(1): clause for clause in clauses}
        self.assertEqual(set(by_status), {"closed", "auto-closed"}, write)
        self.assertTrue(by_status["closed"].startswith("Close:"), by_status["closed"])
        self.assertTrue(by_status["auto-closed"].startswith("Auto-close:"), by_status["auto-closed"])
        self.assertIn("before the new Day", by_status["auto-closed"])
        for clause in re.split(r"[.;]", self.text):
            if "`status:" in clause:
                self.assertRegex(clause.strip(), r"^(Close|Auto-close):", clause)

    def test_both_close_modes_clear_the_open_day(self):
        """Acceptance #26: the close clears `state.md` `open_day` in the same
        commit, whichever mode wrote the status."""
        write = self.section(self.text, "Write")
        both = self.one_line_with(write, "Both:").split("Both:", 1)[1]
        self.assertIn("`state.md`", both)
        self.assertIn('`open_day: ""`', both)
        self.assertIn("`close-day: <date> <verdict>`", both)

    def test_the_refresh_mode_keeps_the_status_the_state_and_the_log_commit(self):
        """PR #32 review 2: a log into a closed Day rebuilds the Summary through
        this routine's `Refresh` mode, so the Summary algorithm is stated once.
        Refresh keeps the `closed` or `auto-closed` status, leaves `state.md`
        `open_day` as it is and writes no `close-day:` commit of its own."""
        write = self.section(self.text, "Write")
        refresh = write.split("Refresh:", 1)[1]
        self.assertIn("Summary only", refresh)
        self.assertIn("status", refresh)
        self.assertIn("`open_day` stay", refresh)
        self.assertIn("no own commit", refresh)
        self.assertNotIn("`status:", refresh)
        self.assertNotIn("close-day:", refresh)

    def test_the_table_step_matches_the_lint_header_and_the_total_row(self):
        rule = self.step(self.steps, 2)
        self.assertIn(f"`{SUMMARY_TABLE_HEADER}`", rule)
        self.assertIn("`| TOTAL | ... |`", rule)
        self.assertIn("a row per filled slot in order", rule)
        self.assertIn("Day totals", rule)

    def test_the_mark_goes_on_every_table_number_of_an_estimated_day(self):
        rule = self.step(self.steps, 2)
        self.assertIn("`estimated: true`", rule)
        self.assertIn("`~` before every number", rule)

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

    def test_the_gap_spelling_and_the_exact_hit_match_the_lint(self):
        """Review items 5 and 7 on PR #32: the lint takes one spelling of the
        gap, the shortest, with a decimal only when the target has one, and one
        word at zero. Step 4 says both, so the agent writes what the lint takes."""
        rule = self.step(self.steps, 4)
        self.assertIn("`0 under`", rule)
        self.assertIn("the target's decimals only", rule)
        self.assertIsNotNone(SUMMARY_BULLET_RE.match("- kcal 0 under"))
        self.assertIsNone(SUMMARY_BULLET_RE.match("- kcal 0 over"))
        self.assertIsNotNone(SUMMARY_BULLET_RE.match("- protein 66.5 under"))

    def test_the_verdict_words_are_the_fixed_ones(self):
        """Acceptance #26: `on target` when all four macros sit inside the stored
        bounds, else `off target:` with each off macro and its direction."""
        rule = self.step(self.steps, 5)
        self.assertIn("`on target`", rule)
        self.assertIn("inside min and max", rule)
        self.assertIn("`off target: <macro> low|high`", rule)
        self.assertIn("one per off macro", rule)
        # The comma between two off macros is the lint regex and the glossary
        # Verdict term; the routine budget paid for the refresh mode with it.
        self.assertIsNotNone(SUMMARY_VERDICT_RE.match("off target: protein low, fat high"))
        self.assertIn("comma separated", read(VAULT / "CONTEXT.md"))

    def test_the_hint_is_one_optional_last_line(self):
        rule = self.step(self.steps, 6)
        self.assertIn(f"`{SUMMARY_HINT_PREFIX}<one line>`", rule)
        self.assertIn("Last line", rule)
        self.assertIn("when useful", rule)

    def test_unreviewed_foods_are_named_and_one_ok_reviews_them_all(self):
        """Acceptance #26: the reply ends with one line naming unreviewed Foods
        eaten today; "ok" reviews them all."""
        rule = self.step(self.steps, 7)
        self.assertIn("Name the Day's unreviewed Foods", rule)  # the Day of step 1, which an auto-close or a refresh closes for a past date
        self.assertIn('"ok": `reviewed: true` on all', rule)
        self.assertIn("commit `close-day: reviewed <names>`", rule)

    def test_the_write_closes_clears_and_commits_in_one_step(self):
        """Acceptance #26: the Summary, the status, the cleared State and the
        commit are one step. The one `close-day:` commit message is named once;
        the second "commit" is the refresh saying it writes none."""
        write = self.section(self.text, "Write")
        for needle in ("`## Summary`", "`status: closed`", "`state.md`", '`open_day: ""`', "`updated`", "`close-day: <date> <verdict>`"):
            self.assertIn(needle, write)
        self.assertEqual(write.count("`close-day: <date> <verdict>`"), 1)

    def test_the_reply_has_the_table_the_verdict_the_hint_and_the_unreviewed_line(self):
        """The reply repeats what the steps built, so it names them instead of
        restating their shape; the `~` of an estimated Day rides on the table of
        step 2."""
        reply = self.section(self.text, "Reply")
        for needle in ("Steps 2, 5-7", "none: no line"):
            self.assertIn(needle, reply)

    def test_a_log_into_a_closed_day_points_at_the_close_day_refresh(self):
        """PR #32 review 2: `routines/log.md` step 1 names the refresh path of
        this file, so the Summary algorithm lives here only."""
        log = read(LOG)
        self.assertIn("closed Day: `routines/close-day.md` refresh", log)
        for shape in ("| slot |", "over|under", "on target"):
            self.assertNotIn(shape, log)


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
        self.assertIn('"last week" is the previous one', rule)
        self.assertIn("no rolling window", rule)

    def test_the_denominator_is_the_eligible_dates_not_seven(self):
        """PR #32 review 6: "this week" is Monday to today, so a Wednesday
        review has three eligible dates, not seven, and the reply prints that
        number. A date still to come is never reported as missing."""
        rule = self.step(self.steps, 1)
        self.assertIn("Eligible dates", rule)
        self.assertIn("this week Monday to today", rule)
        self.assertIn("last week all seven", rule)
        self.assertIn("future dates never missing", rule)
        days = self.one_line_with(self.section(self.text, "Reply"), "`Days:")
        self.assertIn("of <eligible> closed", days)
        self.assertNotIn("of 7", self.text)

    def test_a_week_with_no_closed_day_has_a_fixed_shape(self):
        """PR #32 review 6: with nothing counted the average has no divisor, so
        the routine fixes the three lines instead of dividing by zero."""
        rule = self.step(self.steps, 5)
        for shape in ("`Average: n/a`", "`On target: 0 of 0`", "`Most common miss: none`"):
            self.assertIn(shape, rule)

    def test_only_closed_days_count_and_the_open_day_gets_one_line(self):
        rule = self.step(self.steps, 2)
        self.assertIn("`status: closed` and `auto-closed` Days only", rule)
        self.assertIn("Today open: left out, say so in one line", rule)
        self.assertIn("Missing: eligible dates with no such Day", rule)
        self.assertIn("state them, never guess", rule)

    def test_the_average_carries_the_mark_when_any_counted_day_is_estimated(self):
        rule = self.step(self.steps, 3)
        self.assertIn("Average per day", rule)
        # The rounding rule is stated once, in log.md step 4; this routine points there.
        self.assertIn("`routines/log.md` step 4", rule)
        self.assertNotIn("half up", self.text)
        self.assertIn("`~` on the average when a counted Day is `estimated: true`", rule)

    def test_days_on_target_and_the_most_common_miss_come_from_the_verdicts(self):
        rule = self.one_line_with(self.steps, "4. Days on target")
        self.assertIn("verdicts reading `on target`", rule)
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

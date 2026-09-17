"""Tests for the seeded-day acceptance run (#28).

The run itself is the acceptance test of the vault; these tests pin the
script's own seams: the shapes it writes parse with the lint, the reply lines
it fixes are the ones the routines fix, the read budget counts what it should,
and one full run on a throwaway clone leaves `main` and the working tree alone.

Run: python3 -m unittest discover acceptance
"""
import datetime
import os
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "lint"))

import seeded_day as sd  # noqa: E402
from vault_lint import (  # noqa: E402
    SUMMARY_BULLET_RE,
    SUMMARY_GOAL_RE,
    SUMMARY_SEPARATOR,
    SUMMARY_TABLE_HEADER,
    SUMMARY_VERDICT_RE,
    parse_entry_line,
    parse_frontmatter,
)

GOALS = {"kcal": Decimal(2500), "protein": Decimal(135), "fat": Decimal(60), "carbs": Decimal(355)}
BOUNDS = {
    "kcal": (Decimal(2375), Decimal(2625)),
    "protein": (Decimal(128), Decimal(142)),
    "fat": (Decimal(57), Decimal(63)),
    "carbs": (Decimal(337), Decimal(373)),
}


class EntryLineTest(unittest.TestCase):
    def test_a_marked_food_line_has_the_canonical_shape(self):
        line = sd.entry_line("Croissant", "60", "g", {"kcal": 244, "protein_g": 5, "fat_g": 13, "carbs_g": 28}, marked=True)
        self.assertEqual(line, "- ~ [[Croissant]] = 60 g — 244 kcal · 5 P · 13 F · 28 C")
        entry = parse_entry_line(line)
        self.assertEqual((entry.name, entry.unit, entry.marked, entry.macros["kcal"]), ("Croissant", "g", True, 244))

    def test_a_meal_line_by_portion_with_an_ingredient_change_parses(self):
        line = sd.entry_line("Usual breakfast", "1", "portion", {"kcal": 540, "protein_g": 46, "fat_g": 7, "carbs_g": 67},
                             change=("Skyr", "300"))
        self.assertEqual(line, "- [[Usual breakfast]] = 1 portion, [[Skyr]] = 300 g — 540 kcal · 46 P · 7 F · 67 C")
        self.assertEqual(parse_entry_line(line).change, ("Skyr", Decimal(300)))


class FrontmatterTest(unittest.TestCase):
    def test_render_round_trips_through_the_lint_parser(self):
        text = sd.render_frontmatter([("type", "day"), ("goal", '"[[Goals]]"'), ("aliases", ["Kipferl", "Buttercroissant"]),
                                      ("estimated", "true")])
        data, body = parse_frontmatter(text + "\n## Breakfast\n")
        self.assertEqual(data["type"], "day")
        self.assertEqual(data["goal"], "[[Goals]]")
        self.assertEqual(data["aliases"], ["Kipferl", "Buttercroissant"])
        self.assertEqual(body.strip(), "## Breakfast")


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.slot_sums = {
            "breakfast": {"kcal": 784, "protein_g": 51, "fat_g": 20, "carbs_g": 95},
            "dinner": {"kcal": 336, "protein_g": 30, "fat_g": 24, "carbs_g": 1},
        }
        self.totals = {"kcal": 1120, "protein_g": 81, "fat_g": 44, "carbs_g": 96}

    def test_the_verdict_names_each_off_macro_once_in_column_order(self):
        totals = {"kcal": Decimal(1862), "protein": Decimal(141), "fat": Decimal(46), "carbs": Decimal(212)}
        self.assertEqual(sd.verdict(totals, BOUNDS), "off target: kcal low, fat low, carbs low")
        self.assertRegex(sd.verdict(totals, BOUNDS), SUMMARY_VERDICT_RE)
        inside = {"kcal": Decimal(2500), "protein": Decimal(130), "fat": Decimal(63), "carbs": Decimal(340)}
        self.assertEqual(sd.verdict(inside, BOUNDS), "on target")
        high = dict(inside, fat=Decimal(64))
        self.assertEqual(sd.verdict(high, BOUNDS), "off target: fat high")

    def test_the_summary_lines_follow_the_lint_shape_with_the_mark(self):
        lines = sd.render_summary(self.slot_sums, self.totals, GOALS, BOUNDS, marked=True, hint="Add a grain at dinner.")
        self.assertEqual(lines[0], SUMMARY_TABLE_HEADER)
        self.assertEqual(lines[1], SUMMARY_SEPARATOR)
        self.assertEqual(lines[2], "| breakfast | ~784 | ~51 | ~20 | ~95 |")
        self.assertEqual(lines[3], "| dinner | ~336 | ~30 | ~24 | ~1 |")
        self.assertEqual(lines[4], "| TOTAL | ~1120 | ~81 | ~44 | ~96 |")
        self.assertEqual(lines[5], "")
        self.assertRegex(lines[6], SUMMARY_GOAL_RE)
        self.assertEqual(lines[6], "Goal 2500 kcal (2375-2625), 135 P (128-142), 60 F (57-63), 355 C (337-373).")
        bullets = lines[8:12]
        self.assertEqual(bullets, ["- kcal 1380 under", "- protein 54 under", "- fat 16 under", "- carbs 259 under"])
        for bullet in bullets:
            self.assertRegex(bullet, SUMMARY_BULLET_RE)
        self.assertEqual(lines[13], "off target: kcal low, protein low, fat low, carbs low")
        self.assertEqual(lines[-1], "Hint: Add a grain at dinner.")

    def test_an_exact_hit_writes_zero_under_and_a_plain_day_has_no_mark(self):
        totals = {"kcal": 2500, "protein_g": 140, "fat_g": 60, "carbs_g": 355}
        lines = sd.render_summary({"lunch": totals}, totals, GOALS, BOUNDS, marked=False, hint=None)
        self.assertEqual(lines[2], "| lunch | 2500 | 140 | 60 | 355 |")
        self.assertIn("- kcal 0 under", lines)
        self.assertIn("- protein 5 over", lines)
        self.assertEqual(lines[-1], "on target")


class ReviewTest(unittest.TestCase):
    def test_the_fixed_lines_of_a_week_with_one_estimated_closed_day(self):
        monday = datetime.date(2026, 9, 14)
        days = [sd.DaySummary(date="2026-09-14", status="closed", estimated=True,
                              totals={"kcal": Decimal(1862), "protein_g": Decimal(141), "fat_g": Decimal(47), "carbs_g": Decimal(213),
                                      "fiber_g": Decimal("11.8"), "sugar_g": Decimal("35.2"), "salt_g": Decimal("2.2")},
                              verdict="off target: kcal low, fat low, carbs low"),
                sd.DaySummary(date="2026-09-15", status="open", estimated=False, totals={}, verdict=None)]
        lines = sd.review_reply(days, GOALS, today=monday + datetime.timedelta(days=1))
        self.assertEqual(lines, [
            "Days: 1 of 2 closed, 0 auto-closed, missing none",
            "Average: ~1862 kcal · ~141 P · ~47 F · ~213 C · ~11.8 fiber · ~35.2 sugar · ~2.2 salt",
            "Target: 2500 kcal · 135 P · 60 F · 355 C",
            "On target: 0 of 1",
            "Most common miss: kcal low, 1 days; fat low, 1 days; carbs low, 1 days",
            "2026-09-15 is open and not counted.",
        ])
        self.assertLess(len(lines), 10)

    def test_a_week_with_nothing_counted_takes_the_fixed_empty_shape(self):
        lines = sd.review_reply([], GOALS, today=datetime.date(2026, 9, 16))
        self.assertEqual(lines[0], "Days: 0 of 3 closed, 0 auto-closed, missing 2026-09-14, 2026-09-15, 2026-09-16")
        self.assertEqual(lines[1], "Average: n/a")
        self.assertEqual(lines[3], "On target: 0 of 0")
        self.assertEqual(lines[4], "Most common miss: none")


class SlotTest(unittest.TestCase):
    def test_word_then_clock_then_next_open_slot(self):
        self.assertEqual(sd.pick_slot("breakfast", datetime.time(13, 0), set()), "breakfast")
        self.assertEqual(sd.pick_slot(None, datetime.time(10, 15), set()), "breakfast")
        self.assertEqual(sd.pick_slot(None, datetime.time(10, 15), {"breakfast"}), "lunch")
        self.assertEqual(sd.pick_slot(None, datetime.time(13, 30), set()), "lunch")
        self.assertEqual(sd.pick_slot(None, datetime.time(16, 0), set()), "snack")
        self.assertEqual(sd.pick_slot(None, datetime.time(19, 30), set()), "dinner")

    def test_a_second_message_into_the_same_slot_stays_when_the_earlier_message_was_this_one(self):
        # The croissant at 10:15 after breakfast from an earlier message lands under lunch by the fixed order;
        # a slot word keeps it under breakfast.
        self.assertEqual(sd.pick_slot("breakfast", datetime.time(10, 15), {"breakfast"}), "breakfast")


class CommitSubjectTest(unittest.TestCase):
    def test_the_shape_is_routine_colon_one_line(self):
        self.assertRegex("log: 2026-09-14 breakfast Usual breakfast 1 portion", sd.COMMIT_SUBJECT_RE)
        self.assertRegex("close-day: 2026-09-14 off target: kcal low", sd.COMMIT_SUBJECT_RE)
        self.assertRegex("create-food: Croissant", sd.COMMIT_SUBJECT_RE)
        self.assertNotRegex("Log: 2026-09-14 breakfast", sd.COMMIT_SUBJECT_RE)
        self.assertNotRegex("log:2026-09-14", sd.COMMIT_SUBJECT_RE)
        self.assertNotRegex("prototype: seed vault", sd.COMMIT_SUBJECT_RE)
        self.assertNotRegex("log: two\nlines", sd.COMMIT_SUBJECT_RE)


class ReadBudgetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name in ("a.md", "b.md", "c.md"):
            (root / name).write_text(name, encoding="utf-8")
        self.session = sd.Session(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_file_counts_once_per_turn_and_a_cached_file_counts_as_used_only(self):
        self.session.begin_turn()
        self.session.read("a.md")
        self.session.read("a.md")
        self.session.read("b.md")
        self.assertEqual(sorted(self.session.reads), ["a.md", "b.md"])
        self.session.begin_turn()
        self.session.read("a.md")
        self.session.read("c.md")
        self.assertEqual(sorted(self.session.reads), ["c.md"], "a.md is in context from the earlier turn")
        self.assertEqual(sorted(self.session.used), ["a.md", "c.md"])

    def test_a_write_drops_the_file_from_context_so_the_next_read_is_fresh(self):
        self.session.begin_turn()
        self.session.read("a.md")
        self.session.write("a.md", "new")
        self.session.begin_turn()
        self.assertEqual(self.session.read("a.md"), "new")
        self.assertEqual(sorted(self.session.reads), ["a.md"])

    def test_a_new_session_starts_with_an_empty_context(self):
        self.session.begin_turn()
        self.session.read("a.md")
        self.session.begin_session()
        self.session.begin_turn()
        self.session.read("a.md")
        self.assertEqual(sorted(self.session.reads), ["a.md"])


def working_tree_files() -> list[str]:
    """Every tracked or new file of the repository's working tree, ignored files left out."""
    listed = sd.git(REPO, "ls-files", "--cached", "--others", "--exclude-standard")
    return [line for line in listed.split("\n") if line]


def clone_with_working_tree(parent: Path) -> Path:
    """A clone of this repository with the working tree as one commit on top of HEAD.

    The clone stands in for the owner's checkout, so a run from the pre-commit
    hook tests the files about to be committed and not the previous commit.
    """
    clone = parent / "vault"
    sd.git(parent, "clone", "-q", str(REPO), str(clone))
    sd.git(clone, "config", "user.email", "run@example.invalid")
    sd.git(clone, "config", "user.name", "Acceptance run")
    sd.git(clone, "rm", "-rq", "--cached", ".")
    for rel in working_tree_files():
        source, target = REPO / rel, clone / rel
        if source.is_symlink():
            target.unlink(missing_ok=True)
            target.symlink_to(os.readlink(source))
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    sd.git(clone, "add", "-A")
    sd.git(clone, "commit", "-q", "--allow-empty", "-m", "acceptance: the working tree of the checkout")
    return clone


BROKEN_FOOD = """---
type: food
name: Broken
category: grain
kcal_per_100g: 100
protein_g_per_100g: 1
fat_g_per_100g: 1
carbs_g_per_100g: 1
fiber_g_per_100g: 0
sugar_g_per_100g: 0
salt_g_per_100g: 0
label_basis: 100g
number_source: database
source_ref: test
source_date: 2026-09-14
reviewed: false
---
"""
"""A Food node the lint rejects: nothing in index.md points at it."""

BROKEN_INDEX_LINE = "- [[Broken]] | grain"
"""The Index line that repairs the vault: adding it makes the lint accept Broken."""


def write_broken_food(session: sd.Session) -> None:
    """Write the Food the lint rejects. This is the step of commit A."""
    session.write("nodes/food/Broken.md", BROKEN_FOOD)


def repair_broken_food(session: sd.Session) -> None:
    """Point the Index at the Food, which is what the lint misses. This is the step of commit B."""
    session.write("index.md", sd._insert_index_line(session.read("index.md"), "Food", BROKEN_INDEX_LINE))


def subjects_since(clone: Path, head: str) -> list[str]:
    listed = sd.git(clone, "log", "--format=%s", f"{head}..HEAD")
    return [line for line in listed.split("\n") if line]


class CommitLintGateTest(unittest.TestCase):
    """`Session.commit()` holds the lint gate on the tree it just committed (#28).

    The reason the gate sits there and not on the turn is in the docstring of
    `Session.commit()`. These tests drive a two-commit turn on a real clone
    with the real lint, so they prove the committed tree is linted.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.clone = clone_with_working_tree(Path(cls.tmp.name))
        cls.start = sd.git(cls.clone, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.head_before = self.start
        self.session = sd.Session(self.clone)
        self.session.begin_turn()

    def tearDown(self):
        sd.git(self.clone, "reset", "-q", "--hard", self.start)
        sd.git(self.clone, "clean", "-qfd")

    def add_index_line(self) -> None:
        repair_broken_food(self.session)

    def new_subjects(self) -> list[str]:
        return subjects_since(self.clone, self.head_before)

    def test_the_first_commit_of_a_turn_fails_the_run_before_the_repairing_commit(self):
        def two_commit_turn():
            write_broken_food(self.session)
            self.session.commit("create-food: Broken")
            self.add_index_line()
            self.session.commit("log: 2026-09-14 breakfast Broken 60 g")

        with self.assertRaises(sd.Failed) as caught:
            two_commit_turn()
        message = str(caught.exception)
        self.assertIn("vault lint", message)
        self.assertIn("create-food: Broken", message)
        self.assertIn("nodes/food/Broken.md", message, "the message must name the file of the committed tree")
        self.assertEqual(self.new_subjects(), ["create-food: Broken"], "commit A landed, commit B never ran")
        self.assertEqual(sd.git(self.clone, "log", "--format=%s", "-1"), "create-food: Broken")
        self.assertNotEqual(sd.git(self.clone, "rev-parse", "HEAD"), self.head_before)
        self.assertEqual(self.session.commits, [], "a commit the lint rejects is not recorded green")

    def test_the_lint_reads_the_committed_tree_and_not_the_working_tree(self):
        write_broken_food(self.session)
        with self.assertRaises(sd.Failed):
            self.session.commit("create-food: Broken")
        self.assertEqual(sd.git(self.clone, "status", "--porcelain"), "",
                         "the committed tree is the working tree, so linting the path lints the commit")
        self.assertEqual(sd.git(self.clone, "show", "--name-only", "--format=", "HEAD").strip(), "nodes/food/Broken.md")

    def test_a_valid_commit_passes_and_records_its_lint_result(self):
        write_broken_food(self.session)
        self.add_index_line()
        sha = self.session.commit("create-food: Broken")
        self.assertEqual(self.new_subjects(), ["create-food: Broken"])
        self.assertEqual(self.session.commits, [sd.CommitRecord("create-food: Broken", sha)])
        self.assertEqual(sd.git(self.clone, "status", "--porcelain"), "")

    def test_a_subject_that_is_not_routine_colon_one_line_fails_before_the_commit(self):
        write_broken_food(self.session)
        self.add_index_line()
        with self.assertRaises(sd.Failed):
            self.session.commit("Created a food")
        self.assertEqual(self.new_subjects(), [], "a bad subject makes no commit")

    def test_the_records_of_a_turn_start_empty(self):
        write_broken_food(self.session)
        self.add_index_line()
        self.session.commit("create-food: Broken")
        self.session.begin_turn()
        self.assertEqual(self.session.commits, [])


class TwoCommitRun(sd.Run):
    """A run of one turn that chains a breaking commit and a repairing commit.

    `turns()` is the seam of `Run`: this subclass replaces the seeded ten
    turns with two turns of its own. `reached` collects the work after the
    breaking commit, so an empty `reached` means the gate stopped the run.
    """

    def __init__(self, vault: Path, out):
        super().__init__(vault, datetime.date(2026, 9, 14), out)
        self.reached: list[str] = []

    def two_commit_turn(self) -> sd.Reply:
        write_broken_food(self.session)
        self.session.commit("create-food: Broken")
        self.reached.append("the repairing commit")
        repair_broken_food(self.session)
        self.session.commit("log: 2026-09-14 breakfast Broken 60 g")
        return sd.Reply(["Logged."])

    def later_turn(self) -> sd.Reply:
        self.reached.append("the later turn")
        return sd.Reply(["Never."])

    def check(self, reply, commits) -> None:
        self.reached.append("the check of the turn")

    def turns(self):
        return [
            ("08:30", "Log the broken food.", self.two_commit_turn, self.check),
            ("08:40", "Log something else.", self.later_turn, self.check),
        ]


class RunGateTest(unittest.TestCase):
    """The gate stops the run and not only the session (#28).

    `Session.commit()` raises, but the runner must carry that up: no later
    routine step, no later turn, nothing reported. This test drives
    `Run.execute()` on a real clone with the real lint.
    """

    def test_a_broken_first_commit_stops_the_run_before_the_repairing_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = clone_with_working_tree(Path(tmp))
            head_before = sd.git(clone, "rev-parse", "HEAD")
            lines: list[str] = []
            runner = TwoCommitRun(clone, lines.append)
            report = sd.Report("acceptance/test")

            with self.assertRaises(sd.Failed) as caught:
                runner.execute(report)

            self.assertIn("vault lint", str(caught.exception))
            self.assertIn("create-food: Broken", str(caught.exception))
            self.assertEqual(runner.reached, [], "the run went on after the commit the lint rejects")
            self.assertEqual(report.turns, [], "a turn with a rejected commit is not reported")
            self.assertEqual(subjects_since(clone, head_before), ["create-food: Broken"])
            self.assertNotIn("Broken", sd.git(clone, "show", "HEAD:index.md"), "the repairing commit landed")


class FullRunTest(unittest.TestCase):
    """One full run on a throwaway clone that carries this repository's working tree.

    The clone gets the working tree as one commit on top of HEAD, so a run
    from the pre-commit hook tests the files about to be committed and not the
    previous commit. The clone stands in for the owner's checkout; the run
    itself makes its branch and worktree and removes both. `main` and the
    working tree of the clone stay as they were.
    """

    def test_the_run_passes_and_leaves_no_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = clone_with_working_tree(Path(tmp))
            head_before = sd.git(clone, "rev-parse", "HEAD")
            branches_before = sd.git(clone, "branch", "--list")
            lines: list[str] = []
            report = sd.run(clone, datetime.date(2026, 9, 14), keep=False, out=lines.append)
            self.assertTrue(report.ok, "\n".join(lines))
            self.assertEqual(len(report.turns), 10)
            self.assertEqual([c.split(":")[0] for c in report.commit_subjects],
                             ["log", "create-food", "log", "log", "log", "close-day", "log"])
            for subject in report.commit_subjects:
                self.assertRegex(subject, sd.COMMIT_SUBJECT_RE)
            self.assertTrue(all(turn.reads < sd.READ_BUDGET for turn in report.turns))
            self.assertEqual(sd.git(clone, "rev-parse", "HEAD"), head_before)
            self.assertEqual(sd.git(clone, "branch", "--list"), branches_before)
            self.assertEqual(sd.git(clone, "status", "--porcelain"), "")
            self.assertFalse((clone / "nodes" / "day").exists())
            records = [record for turn in report.turns for record in turn.commits]
            self.assertEqual([record.subject for record in records], report.commit_subjects,
                             "every commit of the run went through the gate in Session.commit()")
            self.assertTrue(all(record.sha for record in records))


if __name__ == "__main__":
    unittest.main()

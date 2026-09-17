"""docs/spec/layout.md and docs/spec/routines.md match the files on main (#28).

The spec documents are the source for a rebuild, so every rule they state is
read back out of the vault here: the Router hard rules, the routine When
lines, the commit subjects, the fixed review lines, the lint and acceptance
commands, and the glossary terms. A spec line that drifts from its file fails.

Run: python3 -m unittest discover lint
"""
import re
import unittest
from pathlib import Path

from vault_lint import (
    AGENTS_POINTER,
    INDEX_SECTIONS,
    ROUTER_TOKEN_LIMIT,
    ROUTINE_SECTIONS,
    ROUTINE_TOKEN_LIMIT,
    SKILL_FILE,
    skill_rule_line,
)

VAULT = Path(__file__).resolve().parent.parent
LAYOUT = VAULT / "docs" / "spec" / "layout.md"
ROUTINES_SPEC = VAULT / "docs" / "spec" / "routines.md"
ROUTER = VAULT / "ROUTER.md"
GLOSSARY = VAULT / "CONTEXT.md"
README = VAULT / "README.md"
ROUTINE_ORDER = ("log", "rebalance", "close-day", "create-food", "create-meal", "pantry", "goals", "review")
SPEC_ISSUE = "https://github.com/erodriguezh/food-planner-nutrition/issues/22"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The body of one `## heading` or `### heading` up to the next heading of level two or three."""
    level = "### " if f"\n### {heading}\n" in text else "## "
    marker = f"\n{level}{heading}\n"
    if marker not in text:
        raise AssertionError(f"no `{level}{heading}` heading")
    after = text.split(marker, 1)[1]
    return re.split(r"\n##{1,2} ", after, maxsplit=1)[0]


def flat(text: str) -> str:
    """The text with its line wraps folded, so a quoted phrase is found across a wrapped line."""
    return " ".join(text.split())


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.text = read(LAYOUT)

    def test_every_root_file_and_folder_it_names_exists(self):
        for name in ("ROUTER.md", "AGENTS.md", "CLAUDE.md", "CONTEXT.md", "index.md", "state.md", SKILL_FILE, "README.md",
                     "nodes/food/", "nodes/meal/", "nodes/goals/Goals.md", "nodes/pantry/Pantry.md", "routines/", "docs/research/",
                     "docs/spec/", "lint/vault_lint.py", "acceptance/seeded_day.py", ".githooks/pre-commit", ".github/workflows/lint.yml"):
            self.assertIn(f"`{name}`", self.text, name)
            self.assertTrue((VAULT / name).exists(), f"{name} named in layout.md does not exist")

    def test_claude_md_is_the_symlink_the_spec_says(self):
        self.assertTrue((VAULT / "CLAUDE.md").is_symlink())
        self.assertEqual((VAULT / "AGENTS.md").read_text(encoding="utf-8").strip(), AGENTS_POINTER)
        self.assertIn(f"`{AGENTS_POINTER}`", self.text)

    def test_the_router_hard_rules_are_quoted_verbatim(self):
        rules = [line.split(". ", 1)[1] for line in section(read(ROUTER), "Hard rules").split("\n") if re.match(r"^\d+\. ", line)]
        self.assertEqual(len(rules), 6)
        for rule in rules:
            self.assertIn(rule, self.text, rule)

    def test_the_router_budget_and_skill_pointer_are_stated(self):
        self.assertIn(f"under {ROUTER_TOKEN_LIMIT} tokens", self.text)
        self.assertIn(f"one line points to `{SKILL_FILE}`", self.text)

    def test_the_index_sections_are_listed_in_the_lint_order(self):
        line = flat(section(self.text, "Index"))
        positions = [line.index(f"`{name}`") for name in INDEX_SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_the_lint_and_acceptance_commands_are_the_ones_the_hook_and_action_run(self):
        hook = read(VAULT / ".githooks" / "pre-commit")
        action = read(VAULT / ".github" / "workflows" / "lint.yml")
        for command in ("python3 lint/vault_lint.py", "python3 -m unittest discover lint", "python3 -m unittest discover acceptance"):
            self.assertIn(command, self.text, command)
            self.assertIn(command, hook, command)
            self.assertIn(command, action, command)
        self.assertIn("python3 acceptance/seeded_day.py", self.text)
        self.assertNotIn("seeded_day.py", action, "the acceptance run itself is not a CI step; its test runs it on a clone")
        self.assertIn("branches: [main]", action)
        self.assertNotIn("pull_request", action, "#28 asks for every push to main, nothing more")

    def test_the_spec_does_not_repeat_the_skill_rule_line(self):
        rule = skill_rule_line(read(VAULT / SKILL_FILE))
        self.assertIsNotNone(rule)
        for path in (LAYOUT, ROUTINES_SPEC):
            self.assertNotIn(rule, read(path), f"{path.name} repeats the fallback line; only docs/spec/context-mcp.md may")

    def test_the_repository_visibility_difference_is_recorded(self):
        self.assertIn("public", section(self.text, "Repository"))
        self.assertIn("private", section(self.text, "Repository"))


class RoutinesSpecTest(unittest.TestCase):
    def setUp(self):
        self.text = read(ROUTINES_SPEC)
        self.files = {name: read(VAULT / "routines" / f"{name}.md") for name in ROUTINE_ORDER}

    def test_one_section_per_routine_in_the_spec_order(self):
        headings = [line[4:] for line in self.text.split("\n") if line.startswith("### ")]
        self.assertEqual(headings, list(ROUTINE_ORDER))

    def test_the_common_shape_states_the_five_sections_and_the_budget(self):
        common = flat(section(self.text, "Common shape"))
        for name in ROUTINE_SECTIONS:
            self.assertIn(name, common)
        self.assertIn(f"under {ROUTINE_TOKEN_LIMIT} tokens", common)

    def test_each_when_line_is_quoted_from_the_file(self):
        for name, text in self.files.items():
            when = text.split("## When\n", 1)[1].split("\n\n", 1)[0].strip()
            self.assertIn(when, section(self.text, name), f"{name}: When line differs")

    def test_each_commit_subject_of_a_write_section_is_quoted(self):
        for name, text in self.files.items():
            write = text.split("## Write\n", 1)[1].split("\n## ", 1)[0]
            subjects = [span for span in re.findall(r"`([^`]+)`", write) if span.split(":")[0] in ROUTINE_ORDER and ": " in span]
            for subject in subjects:
                self.assertIn(f"`{subject}`", section(self.text, name), f"{name}: commit subject {subject!r} missing")
            if name in ("rebalance", "review"):
                self.assertEqual(subjects, [], name)
                self.assertRegex(section(self.text, name), r"[Ww]rites nothing")

    def test_the_review_reply_lines_are_quoted_from_the_file(self):
        reply = self.files["review"].split("## Reply\n", 1)[1]
        lines = re.findall(r"^`([^`]+)`", reply, re.MULTILINE)
        self.assertEqual(len(lines), 6)
        for line in lines:
            self.assertIn(f"`{line}`", section(self.text, "review"), line)

    def test_the_fixed_create_food_and_close_day_replies_are_quoted(self):
        self.assertIn("Say ok to mark reviewed.", self.files["create-food"])
        self.assertIn("Say ok to mark reviewed.", section(self.text, "create-food"))
        self.assertIn("`close-day: <date> <verdict>`", section(self.text, "close-day"))

    def test_the_log_clock_bands_and_the_rounding_pointers_are_quoted(self):
        step = next(line for line in self.files["log"].split("\n") if line.startswith("3. "))
        hours = re.findall(r"<(\d+)", step)
        self.assertEqual(hours, ["11", "15", "18"])
        log = section(self.text, "log")
        for hour in hours:
            self.assertIn(f"before {hour} ", log)
        common = section(self.text, "Common shape")
        for routine, step_number in (("goals", 4), ("create-food", 4), ("log", 4)):
            self.assertIn(f"`routines/{routine}.md` step {step_number}", common)
            self.assertTrue(any(line.startswith(f"{step_number}. ") and ("round" in line or "half" in line or "decimal" in line)
                                for line in self.files[routine].split("\n")), routine)

    def test_the_acceptance_run_maps_every_turn_to_a_routine(self):
        run = section(self.text, "Acceptance run")
        for name in ("log", "rebalance", "close-day", "create-food", "review"):
            self.assertIn(f"`{name}`", run)
        self.assertIn("ten turns", run)


class GlossaryTest(unittest.TestCase):
    def setUp(self):
        self.text = read(GLOSSARY)

    def test_every_term_is_defined_once(self):
        terms = re.findall(r"^- \*\*([^*]+)\*\*:", self.text, re.MULTILINE)
        duplicates = sorted({t for t in terms if terms.count(t) > 1})
        self.assertEqual(duplicates, [])

    def test_the_new_terms_of_28_are_defined(self):
        for term in ("**Acceptance run**", "**Throwaway branch**", "**Turn**", "**Session**", "**Refresh**", "**Routine step**"):
            self.assertEqual(self.text.count(term), 1, term)

    def test_the_lint_term_names_the_action_and_the_spec_term_names_the_documents(self):
        lint = next(l for l in self.text.split("\n") if l.startswith("- **Lint**:"))
        self.assertIn(".github/workflows/lint.yml", lint)
        spec = next(l for l in self.text.split("\n") if l.startswith("- **Spec**:"))
        for name in ("layout", "nodes", "routines", "context-mcp"):
            self.assertIn(name, spec)


class ReadmeTest(unittest.TestCase):
    def test_the_readme_points_to_the_spec_issue_the_spec_docs_and_the_commands(self):
        text = read(README)
        self.assertIn(SPEC_ISSUE, text)
        self.assertIn("docs/spec/", text)
        for command in ("python3 lint/vault_lint.py", "python3 -m unittest discover lint", "python3 -m unittest discover acceptance",
                        "python3 acceptance/seeded_day.py"):
            self.assertIn(command, text, command)
        self.assertNotIn("There is no GitHub Action", text)
        self.assertIn(".github/workflows/lint.yml", text)


if __name__ == "__main__":
    unittest.main()

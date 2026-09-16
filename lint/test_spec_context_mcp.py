"""The Context MCP wiring of #27: one skill file, one Router pointer, one rule.

The rule lives in one skill file at the vault root. The Router points to it in
one line. The spec document states the contract for a rebuild and hands the
internals to the internals map (#19). No other file repeats the rule.

The contract itself gets no test here. #22 sets the boundary: "The Context MCP
contract gets no test in this spec. Its test seam is build_context(question)
and belongs to the internals map (#19)." So the tool signature, the five packet
fields, the status values, the may-add-never-remove rule and the exact fallback
line are not asserted in this file, and this file holds no surrogate test for
`build_context`. What stays is build and wiring regression: the files exist,
they point at each other once, the Router keeps its budget, the no-MCP start
path is unchanged, and the two retrieval paths of the skill file stay mutually
exclusive.

Run: python3 -m unittest discover lint
"""
import re
import unittest
from pathlib import Path

from vault_lint import (
    ROUTER_TOKEN_LIMIT,
    SKILL_FILE,
    estimate_tokens,
    skill_rule_line,
    vault_markdown_files,
)

VAULT = Path(__file__).resolve().parent.parent
SKILL = VAULT / SKILL_FILE
ROUTER = VAULT / "ROUTER.md"
AGENTS = VAULT / "AGENTS.md"
GLOSSARY = VAULT / "CONTEXT.md"
SPEC = VAULT / "docs" / "spec" / "context-mcp.md"
SPEC_REL = "docs/spec/context-mcp.md"
INTERNALS_MAP = "https://github.com/erodriguezh/food-planner-nutrition/issues/19"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def lines_with(text: str, needle: str) -> list[str]:
    return [line for line in text.split("\n") if needle in line]


def order_steps(text: str) -> list[str]:
    """The numbered paths of the "## Order" section of the skill file."""
    body = text.split("## Order", 1)[1].split("\n## ", 1)[0]
    return [line.strip() for line in body.split("\n") if re.match(r"^\d+\.", line.strip())]


class SkillFileTest(unittest.TestCase):
    """#27 AC 1: one skill file at the vault root, and its two retrieval paths
    are mutually exclusive. What the file says about the contract is the
    business of the internals map (#19)."""

    def setUp(self):
        self.text = read(SKILL)

    def test_the_skill_file_sits_at_the_vault_root(self):
        self.assertTrue(SKILL.is_file(), SKILL)
        self.assertEqual(SKILL.parent, VAULT)

    def test_the_two_retrieval_paths_are_mutually_exclusive(self):
        # Round 2 review: the successful MCP path replaces the Index read.
        steps = order_steps(self.text)
        self.assertEqual(len(steps), 2, steps)
        connected, fallback = steps
        self.assertIn("build_context", connected)
        self.assertIn("`state.md`", connected)
        self.assertRegex(connected.lower(), r"do not read `index\.md`")
        self.assertNotIn("build_context", fallback)
        self.assertIn("not connected", fallback.lower())
        self.assertLess(fallback.index("`index.md`"), fallback.index("`state.md`"))


class RouterPointerTest(unittest.TestCase):
    """#27 AC 2 and 4: one pointer line, under 500 tokens, and the no-MCP path
    still reads Router, Index and State."""

    def setUp(self):
        self.text = read(ROUTER)

    def test_one_pointer_line_to_the_skill_file(self):
        self.assertEqual(len(lines_with(self.text, f"`{SKILL_FILE}`")), 1)

    def test_the_pointer_line_names_the_context_mcp_and_the_index(self):
        line = lines_with(self.text, f"`{SKILL_FILE}`")[0]
        self.assertIn("Context MCP", line)
        self.assertIn("`index.md`", line)

    def test_the_start_rule_still_reads_index_then_state(self):
        start = self.text.split("## Start every session", 1)[1].split("\n## ", 1)[0]
        steps = [line for line in start.split("\n") if line[:2] in ("1.", "2.")]
        self.assertEqual(len(steps), 2, steps)
        self.assertIn("Context MCP", steps[0])
        self.assertIn(f"`{SKILL_FILE}`", steps[0])
        self.assertIn("`index.md`", steps[0])
        self.assertIn("`state.md`", steps[1])

    def test_stays_under_the_token_limit(self):
        self.assertLess(estimate_tokens(self.text), ROUTER_TOKEN_LIMIT)


class NoCopyOfTheRuleTest(unittest.TestCase):
    """#27 AC 3: no other file in the repo and no app project instruction
    repeats the rule. The line to look for comes from the skill file, so no
    test here states the rule. Keep it that way: the exact wording of the
    line is the business of `SKILL.md` and of the spec document, and the two
    stay equal because test_the_rule_line_lives_in_the_skill_file_and_the_spec_only
    fails as soon as one of them changes the line alone."""

    def setUp(self):
        self.rule = skill_rule_line(read(SKILL))
        self.assertIsNotNone(self.rule, f"{SKILL_FILE} must quote exactly one line")

    def vault_markdown(self):
        for rel, path in vault_markdown_files(VAULT):
            yield rel, read(path)

    def test_the_rule_line_lives_in_the_skill_file_and_the_spec_only(self):
        holders = sorted(rel for rel, text in self.vault_markdown() if self.rule in text)
        self.assertEqual(holders, sorted([SKILL_FILE, SPEC_REL]))

    def test_agents_md_is_the_one_pointer_line(self):
        self.assertEqual(read(AGENTS), "Read ROUTER.md first.\n")

    def test_claude_md_is_a_symlink_to_agents_md(self):
        claude = VAULT / "CLAUDE.md"
        self.assertTrue(claude.is_symlink())
        self.assertEqual(claude.resolve(), AGENTS.resolve())

    def test_the_glossary_points_to_the_skill_file_and_repeats_no_order(self):
        line = lines_with(read(GLOSSARY), "**Context MCP**")[0]
        self.assertIn(f"`{SKILL_FILE}`", line)
        self.assertNotIn("first", line)

    def test_the_glossary_defines_the_evidence_packet_without_the_rule(self):
        hits = lines_with(read(GLOSSARY), "**Evidence packet**")
        self.assertEqual(len(hits), 1)
        self.assertIn(f"`{SKILL_FILE}`", hits[0])

    def test_the_glossary_lint_entry_promises_the_wiring_and_not_the_contract(self):
        line = lines_with(read(GLOSSARY), "**Lint**")[0]
        self.assertIn("skill file", line)
        self.assertIn("wiring", line)

    def test_the_readme_lint_note_promises_the_wiring_and_not_the_contract(self):
        note = lines_with(read(VAULT / "README.md"), "The first command checks")[0]
        self.assertIn("wiring", note)
        self.assertNotIn("contract", note)


class SpecDocumentTest(unittest.TestCase):
    """#27 deliverable: the spec document exists, stays out of daily use and
    hands the internals, and the contract test, to the internals map (#19)."""

    def setUp(self):
        self.text = read(SPEC)

    def test_the_spec_document_exists(self):
        self.assertTrue(SPEC.is_file(), SPEC)

    def test_says_the_agent_never_loads_it(self):
        self.assertIn("never loads this document", self.text)
        self.assertIn(f"`{SKILL_FILE}`", self.text)

    def test_names_the_internals_map_as_owner_of_the_internals(self):
        self.assertIn(INTERNALS_MAP, self.text)
        owner = self.text.split("## Internals", 1)[1]
        for word in ("scoring", "hosting", "auth", "subscription"):
            self.assertIn(word, owner.lower(), word)

    def test_says_the_lint_checks_the_wiring_and_not_the_contract(self):
        note = lines_with(self.text, "vault lint")[0]
        self.assertIn("checks the wiring", note)
        self.assertNotIn("states this contract", self.text)

    def test_hands_the_contract_test_to_the_internals_map(self):
        # #22: the contract gets no test in this spec; its seam belongs to #19.
        owner = self.text.split("## Internals", 1)[1]
        self.assertIn("no test in this spec", owner)


if __name__ == "__main__":
    unittest.main()

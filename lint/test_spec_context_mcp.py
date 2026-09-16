"""The skill file, the Router pointer and docs/spec/context-mcp.md carry the Context MCP rule once (#27).

The rule lives in one skill file at the vault root. The Router points to it
in one line. The spec document states the contract for a rebuild and hands
the internals to the internals map (#19). No other file repeats the rule.

Run: python3 -m unittest discover lint
"""
import unittest
from pathlib import Path

from vault_lint import (
    FALLBACK_LINE,
    PACKET_FIELDS,
    ROUTER_TOKEN_LIMIT,
    SKILL_FILE,
    estimate_tokens,
)

VAULT = Path(__file__).resolve().parent.parent
SKILL = VAULT / SKILL_FILE
ROUTER = VAULT / "ROUTER.md"
AGENTS = VAULT / "AGENTS.md"
GLOSSARY = VAULT / "CONTEXT.md"
SPEC = VAULT / "docs" / "spec" / "context-mcp.md"
INTERNALS_MAP = "https://github.com/erodriguezh/food-planner-nutrition/issues/19"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def lines_with(text: str, needle: str) -> list[str]:
    return [line for line in text.split("\n") if needle in line]


class SkillFileTest(unittest.TestCase):
    """#27 AC 1: the skill file states the tool, the five fields and their
    meaning, the "may add, never remove" rule, the call order and the exact
    fallback line."""

    def setUp(self):
        self.text = read(SKILL)

    def test_the_skill_file_sits_at_the_vault_root(self):
        self.assertTrue(SKILL.is_file(), SKILL)
        self.assertEqual(SKILL.parent, VAULT)

    def test_names_the_one_tool(self):
        self.assertIn("`build_context(question)`", self.text)

    def test_the_five_fields_are_the_contract_fields(self):
        self.assertEqual(PACKET_FIELDS, ("node", "section", "linked", "status", "index_version"))

    def test_each_packet_field_has_one_line_with_its_meaning(self):
        for name in PACKET_FIELDS:
            hits = lines_with(self.text, f"`{name}`")
            self.assertEqual(len(hits), 1, f"expected one line with `{name}`, got {hits}")
            meaning = hits[0].split(f"`{name}`", 1)[1].strip(" :—-")
            self.assertTrue(meaning, f"`{name}` carries no meaning")

    def test_status_names_both_values(self):
        line = lines_with(self.text, "`status`")[0]
        self.assertIn("`ok`", line)
        self.assertIn("`not_found`", line)

    def test_states_the_may_add_never_remove_rule(self):
        self.assertIn("may add", self.text.lower())
        self.assertIn("never remove", self.text.lower())

    def test_states_the_call_order(self):
        text = self.text.lower()
        self.assertIn("first", text)
        self.assertIn("`index.md`", self.text)
        self.assertIn("`state.md`", self.text)

    def test_states_the_exact_fallback_line_once_in_quotes(self):
        self.assertEqual(self.text.count(f'"{FALLBACK_LINE}"'), 1)

    def test_names_both_fallback_triggers(self):
        self.assertIn("`not_found`", self.text)
        self.assertIn("down", self.text.lower())

    def test_holds_no_internals(self):
        for word in ("scoring", "Cloudflare", "OAuth", "Stripe", "subscription"):
            self.assertNotIn(word.lower(), self.text.lower(), word)


class RouterPointerTest(unittest.TestCase):
    """#27 AC 2 and 4: one pointer line, under 500 tokens, and the no-MCP path
    still reads Router, Index and State."""

    def setUp(self):
        self.text = read(ROUTER)

    def test_one_pointer_line_to_the_skill_file(self):
        self.assertEqual(len(lines_with(self.text, f"`{SKILL_FILE}`")), 1)

    def test_the_pointer_line_names_the_context_mcp(self):
        line = lines_with(self.text, f"`{SKILL_FILE}`")[0]
        self.assertIn("Context MCP", line)

    def test_the_router_does_not_repeat_the_rule(self):
        self.assertNotIn("build_context", self.text)
        self.assertNotIn(FALLBACK_LINE, self.text)

    def test_the_start_rule_still_reads_index_then_state(self):
        start = self.text.split("## Start every session", 1)[1].split("\n## ", 1)[0]
        steps = [line for line in start.split("\n") if line[:2] in ("1.", "2.")]
        self.assertEqual(len(steps), 2, steps)
        self.assertIn("`index.md`", steps[0])
        self.assertIn("`state.md`", steps[1])

    def test_stays_under_the_token_limit(self):
        self.assertLess(estimate_tokens(self.text), ROUTER_TOKEN_LIMIT)


class NoCopyOfTheRuleTest(unittest.TestCase):
    """#27 AC 3: no other file in the repo and no app project instruction
    repeats the rule."""

    def vault_markdown(self):
        for path in sorted(VAULT.rglob("*.md")):
            rel = path.relative_to(VAULT).as_posix()
            if any(part.startswith(".") for part in rel.split("/")):
                continue
            yield rel, read(path)

    def test_the_fallback_line_lives_in_the_skill_file_and_the_spec_only(self):
        holders = sorted(rel for rel, text in self.vault_markdown() if FALLBACK_LINE in text)
        self.assertEqual(holders, sorted([SKILL_FILE, "docs/spec/context-mcp.md"]))

    def test_the_packet_fields_are_listed_in_the_skill_file_and_the_spec_only(self):
        holders = sorted(rel for rel, text in self.vault_markdown() if all(f"`{f}`" in text for f in PACKET_FIELDS))
        self.assertEqual(holders, sorted([SKILL_FILE, "docs/spec/context-mcp.md"]))

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

    def test_the_glossary_defines_the_skill_file(self):
        self.assertEqual(len(lines_with(read(GLOSSARY), "**Skill file**")), 1)


class SpecDocumentTest(unittest.TestCase):
    """#27 deliverable and AC 5: docs/spec/context-mcp.md states the contract,
    the read-only rule, the rebuild trigger, the fallback and the auth
    requirement, and names #19 as the owner of the internals."""

    def setUp(self):
        self.text = read(SPEC)

    def test_names_the_tool_and_its_one_argument(self):
        self.assertIn("`build_context(question: string)`", self.text)

    def test_lists_each_packet_field_as_a_table_row(self):
        for name in PACKET_FIELDS:
            rows = [line for line in self.text.split("\n") if line.startswith(f"| `{name}` |")]
            self.assertEqual(len(rows), 1, name)

    def test_states_the_may_add_never_remove_rule(self):
        self.assertIn("may add fields and may never remove one", self.text)

    def test_states_the_read_only_rule(self):
        self.assertIn("Read-only", self.text)
        self.assertNotIn("push_files", self.text)

    def test_states_the_rebuild_trigger(self):
        self.assertIn("each push to `main`", self.text)

    def test_states_the_fallback_with_the_exact_line(self):
        self.assertIn(f'"{FALLBACK_LINE}"', self.text)
        self.assertIn(f"`{SKILL_FILE}`", self.text)

    def test_states_the_auth_requirement(self):
        self.assertIn("paying subscribers", self.text)

    def test_names_the_internals_map_as_owner_of_the_internals(self):
        self.assertIn(INTERNALS_MAP, self.text)
        owner = self.text.split("## Internals", 1)[1]
        for word in ("scoring", "hosting", "auth", "subscription"):
            self.assertIn(word, owner.lower(), word)

    def test_says_the_agent_never_loads_it(self):
        self.assertIn("never loads this document", self.text)

    def test_the_nodes_spec_does_not_own_the_contract(self):
        self.assertNotIn("build_context", read(VAULT / "docs" / "spec" / "nodes.md"))


if __name__ == "__main__":
    unittest.main()

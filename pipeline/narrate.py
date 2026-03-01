"""Converts the markdown briefing into a narration-ready spoken script."""
import re
import logging
from pathlib import Path

import mistune

log = logging.getLogger(__name__)

_INTRO_TEMPLATE = """\
Welcome to the Weekly Developer Radar — your concise intelligence briefing on \
what's moving fast in open-source AI tooling, GitHub Copilot, and developer \
workflows. I'm your host, and this is the week of {date}.

Let's get into it.

"""

_OUTRO_TEMPLATE = """

That's a wrap on this week's Developer Radar. If something caught your eye, \
dig into the links in the show notes. We'll be back next week with another \
round of what's rising, what's stabilising, and what you should actually \
care about. Stay sharp.
"""


class _NarrationRenderer(mistune.BaseRenderer):
    """Renders AST nodes as plain prose suitable for TTS."""

    def _children(self, token, state) -> str:
        return self.render_tokens(token.get('children', []), state)

    def text(self, token, state):
        return token.get('raw', '')

    def paragraph(self, token, state):
        return self._children(token, state).strip() + "\n\n"

    def heading(self, token, state):
        children = self._children(token, state)
        level = token['attrs']['level']
        if level == 1:
            return ""  # title stripped — replaced by intro template
        if level == 2:
            return f"\n\nNext up: {children.strip()}.\n\n"
        return f"{children.strip()}. "

    def list(self, token, state):
        return self._children(token, state)

    def list_item(self, token, state):
        return self._children(token, state).strip() + ". "

    def block_quote(self, token, state):
        return self._children(token, state).strip() + "\n\n"

    def table(self, token, state):
        return ""  # strip tables entirely

    def thematic_break(self, token, state):
        return "\n\n"

    def block_code(self, token, state):
        return ""  # strip code blocks

    def codespan(self, token, state):
        return token.get('raw', '')

    def link(self, token, state):
        return self._children(token, state).strip()

    def image(self, token, state):
        return ""

    def strong(self, token, state):
        return self._children(token, state)

    def emphasis(self, token, state):
        return self._children(token, state)

    def softlinebreak(self, token, state):
        return " "

    def linebreak(self, token, state):
        return "\n"

    def blank_line(self, token, state):
        return ""

    def html(self, token, state):
        return ""

    def inline_html(self, token, state):
        return ""

    def block_text(self, token, state):
        return self._children(token, state)

    def raw_html(self, token, state):
        return ""


def _strip_toc(text: str) -> str:
    """Remove table-of-contents blocks (lines that are mostly links)."""
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        # TOC lines look like: "- [Heading](#anchor)" or "* [text](url)"
        if re.match(r"^\s*[-*]\s+\[.+\]\(#.+\)\s*$", line):
            continue
        out.append(line)
    return "".join(out)


def _clean_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _extract_date(markdown: str) -> str:
    """Pull the week date from the briefing heading if present."""
    m = re.search(r"\*\*Week of (.+?)\*\*", markdown)
    return m.group(1) if m else "this week"


def convert(markdown: str) -> str:
    """Convert markdown briefing to spoken narration script."""
    date = _extract_date(markdown)
    markdown = _strip_toc(markdown)

    renderer = _NarrationRenderer()
    md = mistune.create_markdown(renderer=renderer)
    body = md(markdown)
    body = _clean_whitespace(body)

    # Remove the auto-generated footer line (not podcast-friendly)
    body = re.sub(r"Briefing generated .+pipeline\.\s*", "", body)

    script = _INTRO_TEMPLATE.format(date=date) + body + _OUTRO_TEMPLATE
    log.info("Narration script: %d chars", len(script))
    return script


def convert_file(
    briefing_path: Path = Path("README.md"),
    script_path: Path | None = None,
) -> str:
    markdown = briefing_path.read_text(encoding="utf-8")
    script = convert(markdown)
    if script_path:
        script_path.write_text(script, encoding="utf-8")
        log.info("Script written to %s", script_path)
    return script

"""Assembles the weekly markdown briefing (README.md) from research results."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from .models import ResearchResult

log = logging.getLogger(__name__)

_BRIEFING_PATH = Path("README.md")

_INTRO = """\
# Weekly Developer Radar

> Auto-generated weekly intelligence briefing on fast-rising open-source repos \
in AI agents, GitHub Copilot, MCP, and related developer tooling.

**Week of {date}**

---

"""

_REPO_SECTION = """\
## {rank}. [{full_name}]({url}) — *{status}* (score: {score:.1f})

{key_changes_section}

{implications_section}

> **Takeaway:** {recommendation}

---

"""


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "_No data._"


def build_briefing(results: list[ResearchResult]) -> str:
    date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sections = [_INTRO.format(date=date)]

    for i, r in enumerate(results, start=1):
        section = _REPO_SECTION.format(
            rank=i,
            full_name=r.full_name,
            url=r.url,
            status=r.status,
            score=r.score_total,
            key_changes_section="### Key Changes\n\n" + _bullet_list(r.key_changes),
            implications_section="### Developer Impact\n\n" + _bullet_list(r.implications),
            recommendation=r.recommendation or "_None._",
        )
        sections.append(section)

    sections.append(
        f"*Briefing generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z "
        "by [Weekly Developer Radar](https://github.com) pipeline.*\n"
    )
    return "".join(sections)


def write_briefing(results: list[ResearchResult], path: Path = _BRIEFING_PATH) -> str:
    content = build_briefing(results)
    path.write_text(content, encoding="utf-8")
    log.info("Briefing written to %s (%d chars)", path, len(content))
    return content

"""
Editorial stage — GPT-4o powered narrative synthesis.

Takes all ResearchResult objects from a single episode and produces a
cohesive, non-repetitive spoken podcast script in one GPT-4o call.
This replaces the mechanical narrate.py path when research data is available.
"""
import json
import logging
import os
from datetime import datetime, timezone

from openai import OpenAI

from . import config
from .models import ResearchResult

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an experienced podcast host writing a weekly developer intelligence briefing \
called "Weekly Developer Radar". Your audience is senior engineers and tech leads who \
want signal, not noise.

You will receive structured research data about 5 fast-rising open-source repositories \
from the past week. Your job is to write a complete, ready-to-synthesise spoken podcast \
script — not markdown, not bullet points, flowing spoken prose.

RULES:
- Write the full script from intro to outro. Do not use headings or bullet points.
- Synthesise across all 5 repos. Look for shared themes, tensions, or patterns and \
  call them out explicitly (e.g. "Three of this week's picks are solving the same \
  underlying problem...").
- Vary your sentence openers. Never start two consecutive sentences with the same word \
  or phrase.
- The phrase "this week" may appear at most twice in the entire script.
- Forbidden filler phrases (do not use any of these): "it's worth noting", \
  "it's important to note", "needless to say", "as we can see", "in conclusion", \
  "in summary", "at the end of the day", "moving forward", "let's dive in".
- Each repo section should be 3–5 sentences of narrative, not a list of facts.
- Status labels (Rising & Healthy, Mature & Stable, etc.) may be spoken naturally \
  but don't need to be quoted verbatim.
- Target length: approximately 800–1200 words total (not counting intro/outro which \
  are provided separately and should NOT be reproduced).
- Return only the body of the script — no intro, no outro. Start directly with the \
  first repo segment.
"""


def _build_user_content(results: list[ResearchResult], date: str) -> str:
    payload = {
        "episode_date": date,
        "repos": [
            {
                "rank": i + 1,
                "full_name": r.full_name,
                "status": r.status,
                "score": round(r.score_total, 1),
                "key_changes": r.key_changes,
                "implications": r.implications,
                "recommendation": r.recommendation,
            }
            for i, r in enumerate(results)
        ],
    }
    return json.dumps(payload, indent=2)


def _intro(date: str) -> str:
    return (
        f"Welcome to the Weekly Developer Radar — your concise intelligence briefing on "
        f"what's moving fast in open-source AI tooling, GitHub Copilot, and developer "
        f"workflows. This is the week of {date}.\n\n"
    )


def _outro() -> str:
    return (
        "\n\nThat's the Developer Radar for this week. Every repo we covered today is "
        "linked in the show notes — dig in where something caught your attention. "
        "We'll be back next week with another round of what's rising, what's stabilising, "
        "and what you should actually care about. Stay sharp."
    )


def generate_script(results: list[ResearchResult]) -> str:
    """Generate a cohesive podcast script from all research results."""
    date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ["GITHUB_TOKEN"],
    )

    cfg = config.all_config()["episode"]
    model = cfg.get("editorial_model", "gpt-5.3-codex")
    log.info("Generating editorial narrative for %d repos via %s", len(results), model)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(results, date)},
        ],
        max_tokens=2000,
        temperature=0.7,
    )

    body = response.choices[0].message.content.strip()
    script = _intro(date) + body + _outro()
    log.info("Editorial script: %d chars", len(script))
    return script

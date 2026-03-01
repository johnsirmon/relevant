"""
Reads pending entries from .learnings/*.md, uses GitHub Models to identify
promotable insights, and appends them to .github/copilot-instructions.md.
Marks promoted entries as resolved.
"""
import os
import re
import sys
from datetime import datetime, timezone
from openai import OpenAI

LEARNINGS_DIR = ".learnings"
INSTRUCTIONS_FILE = ".github/copilot-instructions.md"

FILES = ["LEARNINGS.md", "ERRORS.md", "FEATURE_REQUESTS.md"]

SYSTEM_PROMPT = """You are reviewing AI session learnings for a Python podcast pipeline project.

Your job: identify entries that contain non-obvious, broadly applicable facts about THIS codebase
that would help a future Copilot session avoid mistakes or work more effectively.

Rules:
- Only promote entries that are specific, actionable, and not already obvious
- Ignore vague or generic entries
- Output a markdown section titled "## Promoted Learnings" with bullet points
- Each bullet must be a concise, standalone fact (one sentence)
- If nothing qualifies, output exactly: NO_PROMOTIONS
- Do not repeat anything already in the existing instructions
"""


def load_pending_entries() -> str:
    entries = []
    for fname in FILES:
        path = os.path.join(LEARNINGS_DIR, fname)
        if not os.path.exists(path):
            continue
        content = open(path).read()
        # Only include blocks containing "Status**: pending"
        blocks = re.split(r"\n(?=## \[)", content)
        pending = [b for b in blocks if "**Status**: pending" in b]
        if pending:
            entries.append(f"### From {fname}\n" + "\n".join(pending))
    return "\n\n".join(entries)


def get_existing_instructions() -> str:
    if os.path.exists(INSTRUCTIONS_FILE):
        return open(INSTRUCTIONS_FILE).read()
    return ""


def promote(new_section: str):
    existing = get_existing_instructions()
    # Replace existing Promoted Learnings section or append
    marker = "## Promoted Learnings"
    if marker in existing:
        # Merge: extract existing bullets + new bullets, dedupe
        old_match = re.search(r"## Promoted Learnings\n(.*?)(?=\n## |\Z)", existing, re.DOTALL)
        old_bullets = set(old_match.group(1).strip().splitlines()) if old_match else set()
        new_bullets = set(re.sub(r"## Promoted Learnings\n?", "", new_section).strip().splitlines())
        merged = "\n".join(sorted(old_bullets | new_bullets))
        updated = re.sub(r"## Promoted Learnings\n.*?(?=\n## |\Z)", f"{marker}\n{merged}\n", existing, flags=re.DOTALL)
    else:
        updated = existing.rstrip() + f"\n\n{marker}\n{new_section.replace(marker, '').strip()}\n"
    open(INSTRUCTIONS_FILE, "w").write(updated)


def mark_promoted(entry_ids: list[str]):
    for fname in FILES:
        path = os.path.join(LEARNINGS_DIR, fname)
        if not os.path.exists(path):
            continue
        content = open(path).read()
        for eid in entry_ids:
            content = content.replace(
                f"**Status**: pending",
                f"**Status**: promoted\n- **Promoted**: {datetime.now(timezone.utc).isoformat()}",
                1,
            )
        open(path, "w").write(content)


def main():
    pending = load_pending_entries()
    if not pending.strip():
        print("No pending entries found.")
        return

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ["GITHUB_TOKEN"],
    )

    existing = get_existing_instructions()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"EXISTING INSTRUCTIONS:\n{existing}\n\nPENDING ENTRIES:\n{pending}",
            },
        ],
        max_tokens=1000,
    )

    result = response.choices[0].message.content.strip()
    if result == "NO_PROMOTIONS":
        print("No entries qualified for promotion.")
        return

    print(result)
    promote(result)

    # Mark all pending entries as promoted (simple: mark first occurrence per file)
    ids = re.findall(r"\[(LRN|ERR|FEAT)-\d{8}-\w+\]", pending)
    if ids:
        mark_promoted(ids)

    print(f"\n✅ Promoted {len(ids)} entries to {INSTRUCTIONS_FILE}")


if __name__ == "__main__":
    main()

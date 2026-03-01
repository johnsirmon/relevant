#!/usr/bin/env python3
"""Append a correctly formatted entry to a .learnings/ file.

Usage:
    python scripts/log_learning.py \\
        --category ERR \\
        --area tts \\
        --priority high \\
        --summary "edge-tts 7.0.x returns 403" \\
        --details "Microsoft changed endpoint; 7.0.x hard-codes stale URL." \\
        --action "Pin edge-tts>=7.2.7 in requirements.txt"
"""
import argparse
import hashlib
import random
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

_LEARNINGS_DIR = Path(__file__).parent.parent / ".learnings"

_CATEGORY_MAP = {
    "ERR": _LEARNINGS_DIR / "ERRORS.md",
    "LRN": _LEARNINGS_DIR / "LEARNINGS.md",
    "FEAT": _LEARNINGS_DIR / "FEATURE_REQUESTS.md",
}

_VALID_PRIORITIES = ("low", "medium", "high", "critical")
_VALID_AREAS = ("pipeline", "tts", "rss", "narration", "ci", "config", "agent", "skills", "other")


def _generate_id(category: str, now: datetime) -> str:
    date_str = now.strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{category}-{date_str}-{suffix}"


def _format_entry(entry_id: str, category: str, area: str, priority: str,
                  summary: str, details: str, action: str, now: datetime) -> str:
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Map category to LEARNINGS.md sub-category label
    cat_labels = {"ERR": "error", "LRN": "best_practice", "FEAT": "feature_request"}
    cat_label = cat_labels.get(category, category.lower())

    return (
        f"\n## [{entry_id}] {cat_label}\n\n"
        f"**Logged**: {timestamp}\n"
        f"**Priority**: {priority}\n"
        f"**Status**: pending\n"
        f"**Area**: {area}\n\n"
        f"### Summary\n{summary}\n\n"
        f"### Details\n{details}\n\n"
        f"### Suggested Action\n{action}\n"
    )


def _validate(args: argparse.Namespace) -> list[str]:
    errors = []
    if args.category not in _CATEGORY_MAP:
        errors.append(f"--category must be one of: {', '.join(_CATEGORY_MAP)}")
    if args.priority not in _VALID_PRIORITIES:
        errors.append(f"--priority must be one of: {', '.join(_VALID_PRIORITIES)}")
    if not args.summary.strip():
        errors.append("--summary cannot be empty")
    if not args.details.strip():
        errors.append("--details cannot be empty")
    if not args.action.strip():
        errors.append("--action cannot be empty")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a .learnings/ entry")
    parser.add_argument("--category", required=True, choices=list(_CATEGORY_MAP),
                        help="ERR=error, LRN=learning, FEAT=feature request")
    parser.add_argument("--area", required=True, help=f"One of: {', '.join(_VALID_AREAS)}")
    parser.add_argument("--priority", required=True, choices=list(_VALID_PRIORITIES))
    parser.add_argument("--summary", required=True, help="One-line description")
    parser.add_argument("--details", required=True, help="What happened and why")
    parser.add_argument("--action", required=True, help="Specific fix or improvement")
    args = parser.parse_args()

    errors = _validate(args)
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    entry_id = _generate_id(args.category, now)
    target_file = _CATEGORY_MAP[args.category]
    entry = _format_entry(entry_id, args.category, args.area, args.priority,
                          args.summary, args.details, args.action, now)

    with open(target_file, "a", encoding="utf-8") as fh:
        fh.write(entry)

    print(f"Appended {entry_id} to {target_file.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()

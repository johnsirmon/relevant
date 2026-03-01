"""
Pipeline orchestrator.

Usage:
    python -m pipeline.main --podcast          # full pipeline
    python -m pipeline.main --podcast-only     # reuse existing README.md
    python -m pipeline.main --dry-run          # validate without TTS/upload

Env vars:
    PUBLISH_PODCAST=1   equivalent to --podcast
    GITHUB_TOKEN        required for GitHub API and research summarisation
"""
import argparse
import hashlib
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from . import config
from . import briefing as briefing_mod
from . import discover as discover_mod
from . import editorial as editorial_mod
from . import feed as feed_mod
from . import narrate as narrate_mod
from . import research as research_mod
from . import tts as tts_mod
from .models import EpisodeRecord, ResearchResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_MP3_PATH = Path("radar.mp3")
_FEED_PATH = Path("podcast.xml")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_guid(date_str: str) -> str:
    """Deterministic guid keyed on ISO week date."""
    return "radar-" + hashlib.sha1(date_str.encode()).hexdigest()[:12]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _pub_date() -> str:
    return format_datetime(datetime.now(timezone.utc))


def _episode_title() -> str:
    return f"Weekly Developer Radar — {datetime.now(timezone.utc).strftime('%B %d, %Y')}"


def _release_tag() -> str:
    return f"radar-{_today()}"


def _publish_release(mp3_path: Path) -> str:
    """Create or update GitHub Release and return the asset download URL."""
    tag = _release_tag()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    log.info("Publishing release %s", tag)
    create_cmd = [
        "gh", "release", "create", tag, str(mp3_path),
        "--title", f"Radar {_today()}",
        "--notes", "Weekly Developer Radar episode.",
    ]
    upload_cmd = ["gh", "release", "upload", tag, str(mp3_path), "--clobber"]

    result = subprocess.run(create_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.info("Release exists, uploading asset instead")
        subprocess.run(upload_cmd, check=True, capture_output=True)

    # Derive stable asset URL
    url = f"https://github.com/{repo}/releases/download/{tag}/{mp3_path.name}"
    log.info("MP3 hosted at: %s", url)
    return url


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def run_full(args: argparse.Namespace) -> None:
    log.info("=== FULL PIPELINE ===")

    # Idempotency: check if this week's episode is already published
    guid = _build_guid(_today())
    existing = feed_mod.load_existing_guids(_FEED_PATH)
    if guid in existing:
        log.info("Episode %s already published — nothing to do", guid)
        return

    # 1. Discover
    log.info("--- Stage 1: Discover ---")
    repos = discover_mod.discover()

    # 2. Research
    log.info("--- Stage 2: Research ---")
    results = research_mod.research(repos)

    # 3. Briefing
    log.info("--- Stage 3: Briefing ---")
    briefing_mod.write_briefing(results)

    _run_podcast_stages(args, guid, results)


def run_podcast_only(args: argparse.Namespace) -> None:
    log.info("=== PODCAST-ONLY (reusing existing README.md) ===")
    guid = _build_guid(_today())
    existing = feed_mod.load_existing_guids(_FEED_PATH)
    if guid in existing:
        log.info("Episode %s already published — nothing to do", guid)
        return
    _run_podcast_stages(args, guid)


def _run_podcast_stages(args: argparse.Namespace, guid: str, results: list[ResearchResult] | None = None) -> None:
    # 4. Narrate / Editorial
    cfg = config.all_config()["episode"]
    editorial_enabled = cfg.get("editorial_enabled", False)

    if results and editorial_enabled:
        log.info("--- Stage 4: Editorial (AI narrative) ---")
        script = editorial_mod.generate_script(results)
    else:
        log.info("--- Stage 4: Narrate (mechanical renderer) ---")
        script = narrate_mod.convert_file(Path("README.md"))

    # 5. TTS
    log.info("--- Stage 5: TTS ---")
    tts_mod.synthesise(
        script,
        output=_MP3_PATH,
        auto_adjust=args.auto_adjust_duration,
        target_min_min=cfg["target_duration_min"],
        target_max_min=cfg["target_duration_max"],
    )

    # 6. Publish release (must precede feed update)
    log.info("--- Stage 6: Publish Release ---")
    mp3_url = _publish_release(_MP3_PATH)
    file_size = _MP3_PATH.stat().st_size
    duration = tts_mod.get_duration_seconds(_MP3_PATH)

    # 7. Feed update
    log.info("--- Stage 7: Feed Update ---")
    episode = EpisodeRecord(
        title=_episode_title(),
        guid=guid,
        pub_date=_pub_date(),
        mp3_url=mp3_url,
        file_size_bytes=file_size,
        duration_seconds=duration,
    )
    feed_mod.prepend_episode(episode, _FEED_PATH)
    log.info("=== Pipeline complete ===")


def run_dry_run() -> None:
    log.info("=== DRY RUN ===")
    guid = _build_guid(_today())
    existing = feed_mod.load_existing_guids(_FEED_PATH)
    if guid in existing:
        log.info("Episode %s already in feed (dry-run idempotency check passed)", guid)
        return

    placeholder_url = f"https://example.invalid/weekly-radar/{guid}.mp3"
    episode = EpisodeRecord(
        title=_episode_title() + " [DRY RUN]",
        guid=guid,
        pub_date=_pub_date(),
        mp3_url=placeholder_url,
        file_size_bytes=0,
        duration_seconds=0,
    )
    feed_mod.prepend_episode(episode, _FEED_PATH)
    log.info("Dry-run complete — placeholder episode added to feed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly Developer Radar pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--podcast", action="store_true", help="Full pipeline")
    group.add_argument("--podcast-only", action="store_true", help="TTS + publish only")
    group.add_argument("--dry-run", action="store_true", help="Validate without TTS/upload")
    parser.add_argument(
        "--auto-adjust-duration", action="store_true",
        help="Use ffmpeg tempo shift to hit 60±5 min target",
    )
    return parser.parse_args()


def main() -> None:
    # Also honour PUBLISH_PODCAST=1 env var
    if os.environ.get("PUBLISH_PODCAST") == "1" and len(sys.argv) == 1:
        sys.argv.append("--podcast")

    args = _parse_args()

    if args.dry_run:
        run_dry_run()
    elif args.podcast_only:
        run_podcast_only(args)
    else:
        run_full(args)


if __name__ == "__main__":
    main()

# Copilot Instructions

## Self-Improvement

This repo uses a self-improving loop. After each session, log discoveries so future sessions are smarter.

### When to log

| Situation | File |
|-----------|------|
| Command or operation fails unexpectedly | `.learnings/ERRORS.md` |
| You correct yourself or get corrected | `.learnings/LEARNINGS.md` (category: `correction`) |
| Found a better approach | `.learnings/LEARNINGS.md` (category: `best_practice`) |
| Knowledge was wrong or outdated | `.learnings/LEARNINGS.md` (category: `knowledge_gap`) |
| User wants something that doesn't exist yet | `.learnings/FEATURE_REQUESTS.md` |

### Entry format

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: 2026-03-01T18:00:00Z
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: pipeline | tts | rss | narration | ci | config

### Summary
One-line description

### Details
What happened, what was wrong, what's correct

### Suggested Action
Specific fix or improvement
```

Use `LRN-`, `ERR-`, or `FEAT-` prefix. Date + 3-char suffix (e.g. `LRN-20260301-A1B`).

### Promoting to instructions

High-value learnings auto-promote to this file via the **🧠 Self-Improve** GitHub Actions workflow.  
Trigger it from the Actions tab (or it runs automatically when `.learnings/` files change).

## Project Overview

**Weekly Developer Radar Podcast** — a Python pipeline that discovers fast-rising open-source repositories weekly, generates a written briefing, converts it to a narration script, synthesizes audio via TTS, and publishes episodes to an RSS feed with GitHub Release-hosted MP3s.

> This repository is in early setup. Code has not yet been written. The authoritative spec is `prd.md`.

## Planned Architecture

The pipeline runs as `python -m pipeline.main` and is orchestrated by `.github/workflows/update-radar.yml`.

### Module Responsibilities

| File | Role |
|------|------|
| `main.py` | Top-level orchestrator; reads mode flags and runs pipeline stages in order |
| `narrate.py` | Converts `README.md` (markdown briefing) into a spoken narration script |
| `tts.py` | Text-to-speech synthesis; primary: `edge-tts` (free, no auth), fallback: OpenAI TTS via GitHub Models using `GITHUB_TOKEN` (no paid key needed) |
| `podcast.py` | Writes deduped RSS 2.0 + iTunes updates to `podcast.xml` |
| `update-radar.yml` | GitHub Actions workflow; commits artifacts and creates/updates dated GitHub Release |

### Core Artifacts

- `README.md` — weekly markdown briefing (research output)
- `radar.mp3` — generated audio episode
- `podcast.xml` — RSS 2.0 feed with iTunes tags

### Pipeline Stages (in order)

1. Discover repositories from configured topics over last 7 days
2. Score/classify candidates; select top 5
3. Run change-research agent; output markdown briefing to `README.md`
4. `narrate.py` → narration script
5. `tts.py` → `radar.mp3` (primary `edge-tts`, auto-fallback to OpenAI TTS)
6. `podcast.py` → prepend deduped episode to `podcast.xml`
7. Workflow commits artifacts and publishes GitHub Release

## Execution Modes

| Flag / Env Var | Behavior |
|----------------|----------|
| `--podcast` / `PUBLISH_PODCAST=1` | Full pipeline |
| `--podcast-only` | Reuse existing `README.md`, skip discovery/research |
| `--dry-run` | Update `podcast.xml` with placeholder metadata; skip real TTS and MP3 upload |

## Key Conventions

### Ranking Model
- Four indicator categories with configurable weights: **Growth Momentum (35%)**, **Maintenance Health (25%)**, **Engineering Quality (20%)**, **Adoption Signals (20%)**.
- Weights and classification thresholds are externally configurable — do not hard-code them.
- Each analyzed repo must emit both a numeric score and a status class label: `Rising & Healthy`, `Mature & Stable`, `Hype-Driven`, `Niche but Strong`, or `At Risk`.

### Episode Record Schema
Every episode entry written to `podcast.xml` must include: `title`, `guid`, `pub_date` (RFC 2822), `mp3_url` (absolute), `file_size_bytes`.  
Deduplication is by `guid` — never insert a duplicate.

### Episode Duration Target
Audio runtime target is **60 ± 5 minutes**. Script length heuristics may be used during generation, but the pipeline's pass/fail check uses actual audio runtime.

### TTS — No Paid Key Required
Both TTS providers require zero paid credentials:

- **Primary: `edge-tts`** — free, no auth, runs locally via the `edge-tts` Python package.
- **Fallback: OpenAI TTS via GitHub Models** — uses the auto-injected `GITHUB_TOKEN` from GitHub Actions. No OpenAI account or billing required. Endpoint: `https://models.inference.ai.azure.com`, OpenAI-compatible SDK.

```python
from openai import OpenAI
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
)
response = client.audio.speech.create(model="tts-1-hd", voice="alloy", input=script)
```

`tts.py` must automatically attempt the fallback if `edge-tts` fails. Never require a separately managed API key.

### Dry-Run Placeholder URLs
Dry-run must still write a valid episode to `podcast.xml` with a deterministic, clearly-marked non-production placeholder URL. Real TTS is not called.

### Idempotency
The pipeline must be idempotent: re-running on the same input window should not produce duplicate feed entries or duplicate GitHub Releases.

### Narration Script Rules
`narrate.py` must strip visual-only markdown (tables, TOC, link metadata) and preserve story-flow. A consistent intro and outro template must be present in every episode.

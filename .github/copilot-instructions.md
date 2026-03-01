# Copilot Instructions

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
| `tts.py` | Text-to-speech synthesis; primary: `edge-tts`, fallback: OpenAI TTS via `GITHUB_TOKEN` |
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

### TTS Fallback
`tts.py` must automatically attempt the OpenAI TTS fallback (via `GITHUB_TOKEN` → GitHub Models) if `edge-tts` fails. The fallback is not manual — it happens in the same run.

### Dry-Run Placeholder URLs
Dry-run must still write a valid episode to `podcast.xml` with a deterministic, clearly-marked non-production placeholder URL. Real TTS is not called.

### Idempotency
The pipeline must be idempotent: re-running on the same input window should not produce duplicate feed entries or duplicate GitHub Releases.

### Narration Script Rules
`narrate.py` must strip visual-only markdown (tables, TOC, link metadata) and preserve story-flow. A consistent intro and outro template must be present in every episode.

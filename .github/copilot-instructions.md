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

## Commands

```bash
pip install -r requirements.txt

python -m pipeline.main --podcast           # full pipeline
python -m pipeline.main --podcast-only      # reuse existing README.md, skip discovery/research
python -m pipeline.main --dry-run           # update feed with placeholder, skip TTS/upload
python -m pipeline.main --podcast --auto-adjust-duration  # ffmpeg tempo-adjust if duration misses target

PUBLISH_PODCAST=1 python -m pipeline.main   # env var equivalent of --podcast
```

> **Windows / ffmpeg PATH:** winget installs ffmpeg but doesn't update the current shell's PATH. Either open a new terminal after install, or prefix commands with:  
> `$env:PATH = "C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\bin;$env:PATH"`

> **GITHUB_TOKEN:** Use `gh auth token` if GitHub CLI is already authenticated — no manual token management needed:  
> `$env:GITHUB_TOKEN = (gh auth token)`

## Project Overview

**Weekly Developer Radar Podcast** — a Python pipeline that discovers fast-rising open-source repositories weekly, generates a written briefing, converts it to a narration script, synthesizes audio via TTS, and publishes episodes to an RSS feed with GitHub Release-hosted MP3s.

## Architecture

The pipeline runs as `python -m pipeline.main` and is orchestrated by `.github/workflows/update-radar.yml`.

### Module Responsibilities

| Module | Role |
|--------|------|
| `pipeline/main.py` | Orchestrator; wires all stages, parses CLI flags, enforces correct stage order |
| `pipeline/config.py` | Loads `pipeline/config.yaml`; env vars prefixed `RADAR_` override individual keys (dot-path with `__` separator, e.g. `RADAR_WEIGHTS__GROWTH=0.40`) |
| `pipeline/models.py` | Shared dataclasses: `RepoScore`, `ResearchResult`, `EpisodeRecord` |
| `pipeline/discover.py` | PyGithub search by topic, weighted scoring, top-5 selection |
| `pipeline/research.py` | Per-repo activity fetch + GPT-4o summarisation via GitHub Models; results cached to `.cache/research/` |
| `pipeline/briefing.py` | Assembles `README.md` from `ResearchResult` list |
| `pipeline/narrate.py` | mistune AST renderer — strips tables/TOC/links, injects consistent intro + outro |
| `pipeline/tts.py` | edge-tts primary → OpenAI TTS fallback; mutagen duration check; optional ffmpeg tempo adjust |
| `pipeline/feed.py` | RSS 2.0 + iTunes `podcast.xml` updates with guid-based dedup and XML validation |

### Core Artifacts

- `README.md` — weekly markdown briefing (committed)
- `podcast.xml` — RSS 2.0 feed with iTunes tags (committed)
- `radar.mp3` — generated audio episode (`.gitignore`d; hosted via GitHub Release)
- `.cache/research/` — week-keyed API response cache (`.gitignore`d; managed by `actions/cache`)

### Pipeline Stage Order

**Critical: release upload must happen before feed update** — `mp3_url` and `file_size_bytes` are only known post-upload.

1. `discover` — search GitHub by topic, score candidates, select top 5
2. `research` — fetch commits/PRs/releases per repo, summarise with GPT-4o
3. `briefing` — write `README.md`
4. `narrate` — convert `README.md` to spoken script
5. `tts` — synthesise `radar.mp3`
6. **publish release** — `gh release create/upload`, capture final URL + size
7. `feed` — prepend deduped episode to `podcast.xml`

## Execution Modes

| Flag / Env Var | Behavior |
|----------------|----------|
| `--podcast` / `PUBLISH_PODCAST=1` | Full pipeline |
| `--podcast-only` | Reuse existing `README.md`, skip discovery/research |
| `--dry-run` | Update `podcast.xml` with placeholder metadata; skip real TTS and MP3 upload |

## Key Conventions

### Config Loading
All weights, thresholds, and topic list live in `pipeline/config.yaml`. Use `config.get("weights.growth")` for dot-path lookups. Override any value at runtime with `RADAR_<KEY__SUBKEY>=value` env vars — never hard-code scoring values in module code.

### Scoring and Classification
- Repos are sorted by `updated` date first (not raw stars) to surface fast-rising repos, then re-ranked by weighted score.
- Four indicator categories: **Growth (35%)**, **Health (25%)**, **Quality (20%)**, **Adoption (20%)**.
- Status labels (all five must be emitted, never add new ones): `Rising & Healthy`, `Mature & Stable`, `Hype-Driven`, `Niche but Strong`, `At Risk`.
- Classification thresholds are in `config.yaml` under `thresholds` — read them via `config.all_config()["thresholds"]`.

### GUID Strategy
GUIDs are deterministic: `"radar-" + sha1(YYYY-MM-DD)[:12]`. Same date always produces the same GUID, which is how idempotency works — the pipeline checks the existing feed for the current day's GUID at startup and exits early if found.

### Research Cache
`pipeline/research.py` caches raw GitHub API + GPT-4o responses to `.cache/research/<owner>__<repo>__<YYYY-WW>.json`. The cache key is the ISO week number. In CI, `actions/cache` preserves this across re-runs within the same week. Locally the files persist on disk.

### TTS Chunking
Both TTS providers chunk the script at `_CHUNK_SIZE = 4800` chars on paragraph boundaries and concatenate via `ffmpeg -f concat`. Do not pass the full script as a single string — providers have input limits.

### Episode Duration
`mutagen.mp3.MP3` measures actual audio duration. Targets: 55–65 minutes (configurable via `episode.target_duration_min/max` in `config.yaml`). Duration failures log a warning but do not abort the pipeline. The `--auto-adjust-duration` flag triggers a single ffmpeg `atempo` pass (clamped to ±10%).

### Feed Update Rules
- `feed.py` loads existing `podcast.xml` before writing — never replace the file from scratch.
- Dedup by `guid` (checked via `load_existing_guids()` before running TTS).
- `EpisodeRecord.mp3_url` must be the real GitHub Release asset URL, not a placeholder, in non-dry-run mode.
- Dry-run placeholder URL format: `https://example.invalid/weekly-radar/{guid}.mp3`

### Narration Rendering
`pipeline/narrate.py` uses a custom `mistune.BaseRenderer` subclass. Level-1 headings are stripped (replaced by the intro template). Level-2 headings become spoken transitions (`"Next up: ..."`). Tables, images, code blocks, and HTML are silently dropped. Link text is kept, URLs are dropped.

### TTS — No Paid Key Required
Both providers are free with no auth:

- **Primary: `edge-tts`** — free, no auth, `en-US-AriaNeural` voice. Requires `edge-tts>=7.2.7` (7.0.x returns 403 from Microsoft's endpoint).
- **Fallback: `gTTS`** — Google TTS, free, no auth, no API key. Automatically used if edge-tts fails.

> **Note:** GitHub Models does not offer TTS endpoints (only chat models). The `openai` package is kept as a dependency for the research summarisation step only.

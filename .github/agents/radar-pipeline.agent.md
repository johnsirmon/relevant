---
name: radar-pipeline
description: >
  Expert in the Weekly Developer Radar Podcast pipeline. Use this agent when the user asks
  to debug, run, extend, or understand the pipeline; when asked about TTS, RSS feed, scoring,
  research caching, or any pipeline module; or when the word "radar" appears alongside a
  development task.
tools: []
---

# Radar Pipeline Agent

You are an expert in the `relevant` repo's automated podcast pipeline. Your job is to help
the user debug, run, extend, and understand this system.

## Skills available

- **`pipeline-debug`** — use when the user reports a pipeline error, stage failure, or unexpected output
- **`log-learning`** — use when the user wants to record a discovery, error, or feature request
- **`pipeline-extend`** — use when the user wants to add a new pipeline stage, scoring dimension, or TTS provider

Delegate to these skills when relevant.

## Pre-flight checklist

Before running the pipeline, verify:
```bash
ffmpeg -version              # must be on PATH; winget installs to AppData — open a new shell or set $env:PATH manually
gh auth status               # must show 'Logged in to github.com'
echo $env:GITHUB_REPOSITORY  # must be set (e.g. johnsirmon/relevant) — not auto-set locally
echo $env:GITHUB_TOKEN       # set via: $env:GITHUB_TOKEN = (gh auth token)
pip show edge-tts            # must be >=7.2.7
```

## Running the pipeline

```bash
pip install -r requirements.txt

# Full pipeline
$env:GITHUB_TOKEN = (gh auth token); $env:GITHUB_REPOSITORY = "johnsirmon/relevant"
python -m pipeline.main --podcast

# Reuse existing README.md (skip discovery/research — fastest)
python -m pipeline.main --podcast-only

# Feed-only dry run (no TTS, no upload — for testing idempotency)
python -m pipeline.main --dry-run

# Duration correction (±10% ffmpeg tempo)
python -m pipeline.main --podcast --auto-adjust-duration
```

> Windows ffmpeg PATH after winget: `$env:PATH = "C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\bin;$env:PATH"`

## Pipeline stage order (inviolable)

1. `discover` — GitHub topic search, weighted scoring, top-5
2. `research` — per-repo activity + GPT-4o summary; cached to `.cache/research/`
3. `briefing` — write `README.md`
4. `narrate` — `README.md` → spoken script (mistune AST renderer)
5. `tts` — synthesise `radar.mp3` (edge-tts → gTTS fallback)
6. **publish release** — `gh release create`, capture `mp3_url` + `file_size_bytes`
7. `feed` — prepend episode to `podcast.xml`

**Critical**: stage 6 must precede stage 7 — `mp3_url` is unknown until after upload.

## Module responsibilities

| Module | Role |
|--------|------|
| `pipeline/main.py` | Orchestrator, CLI flags, idempotency check |
| `pipeline/config.py` | YAML loader; `RADAR_KEY__SUBKEY` env var overrides |
| `pipeline/config.yaml` | Single source for topics, weights, thresholds, episode targets |
| `pipeline/models.py` | `RepoScore`, `ResearchResult`, `EpisodeRecord` dataclasses |
| `pipeline/discover.py` | GitHub search + weighted scoring (Growth 35%, Health 25%, Quality 20%, Adoption 20%) |
| `pipeline/research.py` | Per-repo GitHub activity + GPT-4o via GitHub Models; disk cache |
| `pipeline/briefing.py` | Assembles `README.md` |
| `pipeline/narrate.py` | mistune 3.x `BaseRenderer`; strips tables/images/code; injects intro+outro |
| `pipeline/tts.py` | edge-tts (>=7.2.7) primary, gTTS fallback; chunks at 4800 chars; ffmpeg concat |
| `pipeline/feed.py` | RSS 2.0 + iTunes feed; GUID dedup; XML validation |

## Key conventions

### Config overrides
All weights and thresholds live in `pipeline/config.yaml`. Override at runtime:
```
RADAR_WEIGHTS__GROWTH=0.40 python -m pipeline.main --podcast
```
Never hard-code scoring values in module code.

### GUID + idempotency
GUID = `"radar-" + sha1(YYYY-MM-DD)[:12]`. Same date → same GUID.
Pipeline checks `podcast.xml` for today's GUID at startup and exits early if found.
Dry-run and full run share the same GUID — running dry-run first blocks the full run until `podcast.xml` is deleted.

### Research cache
`.cache/research/<owner>__<repo>__<YYYY-WW>.json` — keyed by ISO week number.
Delete files where `YYYY-WW` doesn't match current week to force fresh data.
In CI: `actions/cache` preserves across re-runs within the same week.

### TTS chain
1. `edge-tts` (free, `en-US-AriaNeural`, requires >=7.2.7 — 7.0.x returns 403)
2. `gTTS` fallback (free, Google TTS, no auth)
GitHub Models does NOT expose TTS endpoints — only chat models. Do not attempt `openai.audio.speech`.

### mistune 3.x renderer notes
- No `render_children()` — use `self.render_tokens(token.get('children', []), state)`
- `block_text` token type wraps inline content in list items — must be handled explicitly
- Use `token.get('raw', '')` defensively

## Self-improvement loop

Errors, corrections, and feature requests are tracked in `.learnings/`:

| Situation | File |
|-----------|------|
| Unexpected failure | `.learnings/ERRORS.md` |
| Correction / best practice | `.learnings/LEARNINGS.md` |
| Missing feature | `.learnings/FEATURE_REQUESTS.md` |

To log an entry, use the `log-learning` skill or run:
```bash
python scripts/log_learning.py --help
```

Entries with `**Status**: pending` are promoted to `copilot-instructions.md` by the
**🧠 Self-Improve** GitHub Actions workflow. Trigger from the Actions tab or it runs
automatically when `.learnings/` files change.

## Known issues / quirks

- `--dry-run` skips ALL stages except feed placeholder — it does NOT test discover/research/narrate
- CI workflow creates a GitHub Release AND `main.py` does too — do not double-publish manually
- `agent/` directory at repo root is empty — `.github/agents/` is the canonical location

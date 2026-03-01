---
name: pipeline-debug
description: >
  Guide for debugging the Weekly Developer Radar Podcast pipeline. Use this when asked to
  debug a failing pipeline run, investigate a stage error, troubleshoot TTS or audio issues,
  diagnose feed/XML problems, or trace a CI failure.
---

# Pipeline Debug Guide

## Step 1 — Pre-flight checks

Run all of these before anything else:

```bash
ffmpeg -version              # must succeed; if not found, open a new shell after winget install
gh auth status               # must show 'Logged in to github.com'
python -c "import edge_tts; print(edge_tts.__version__)"  # must be >=7.2.7
pip show edge-tts            # check version; upgrade with: pip install --upgrade "edge-tts>=7.2.7"
echo $env:GITHUB_REPOSITORY  # must be set (e.g. johnsirmon/relevant)
echo $env:GITHUB_TOKEN       # set via: $env:GITHUB_TOKEN = (gh auth token)
```

> **Windows ffmpeg PATH:** winget installs ffmpeg but doesn't update the current shell.  
> Fix: `$env:PATH = "C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\bin;$env:PATH"`

## Step 2 — Check known errors

Read `.learnings/ERRORS.md` for previously diagnosed issues. Match the symptom to a known error.

## Step 3 — Isolate the failing stage

| Goal | Command |
|------|---------|
| Test stages 1–5 (skip upload+feed) | `python -m pipeline.main --podcast-only` |
| Test feed/idempotency only (no TTS) | `python -m pipeline.main --dry-run` |
| Run discovery alone | `python -c "from pipeline.discover import discover; print(discover())"` |
| Run narration alone | `python -c "from pathlib import Path; from pipeline.narrate import convert_file; print(convert_file(Path('README.md'))[:500])"` |

> **Do NOT use `--dry-run` to test non-feed stages** — it skips discover, research, briefing, and
> narrate entirely. Use `--podcast-only` to reuse cached research and test everything up to TTS.

## Step 4 — TTS-specific issues

- **edge-tts 403**: upgrade to >=7.2.7 → `pip install --upgrade "edge-tts>=7.2.7"`
- **gTTS fails**: check internet connectivity (gTTS calls Google's API)
- **OpenAI TTS 400 "Unknown model"**: GitHub Models has no TTS endpoint — do not use it
- **ffmpeg concat fails**: verify ffmpeg is on PATH; check temp `.mp3` chunk files were created
- **Duration warning (outside 55–65 min)**: briefing content may be too short; use `--auto-adjust-duration` for a ±10% tempo correction attempt

## Step 5 — Cache issues

Research cache: `.cache/research/<owner>__<repo>__<YYYY-WW>.json`

- Delete files where `YYYY-WW` doesn't match the current ISO week to force a fresh fetch
- Current week: `python -c "from datetime import date; print(date.today().strftime('%Y-W%V'))"`
- Malformed JSON: delete the file and re-run

## Step 6 — Feed / XML issues

```bash
# Validate XML
python -c "import xml.etree.ElementTree as ET; ET.parse('podcast.xml'); print('valid')"

# Check for duplicate GUIDs
python -c "
import xml.etree.ElementTree as ET, hashlib, datetime
today = datetime.date.today().isoformat()
guid = 'radar-' + hashlib.sha1(today.encode()).hexdigest()[:12]
tree = ET.parse('podcast.xml')
guids = [e.text for e in tree.findall('.//{*}guid')]
print('today guid:', guid)
print('existing guids:', guids)
print('duplicate:', guid in guids)
"

# Idempotency blocked? Delete podcast.xml and re-run
Remove-Item podcast.xml
```

## Step 7 — CI-specific issues

- The CI workflow (`update-radar.yml`) AND `pipeline/main.py` both create GitHub Releases.
  In CI, `_publish_release()` runs first inside the Python script; the workflow step is redundant.
  If seeing double-release errors, check that the workflow's `gh release create` step handles `--clobber`.
- `GITHUB_REPOSITORY` is auto-injected in CI; set manually for local runs.
- Research cache is restored via `actions/cache` key `research-YYYY-WNN`. A cache miss forces a full research re-run.

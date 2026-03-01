---
name: pipeline-extend
description: >
  Guide for extending the Weekly Developer Radar Podcast pipeline with a new stage, scoring
  dimension, TTS provider, or configuration value. Use this when the user wants to add new
  functionality to the pipeline.
---

# Pipeline Extension Guide

## Core constraints (never violate these)

1. **Stage order**: discover → research → briefing → narrate → tts → **publish release** → feed  
   The release upload (stage 6) must precede the feed update (stage 7) — `mp3_url` is only known post-upload.
2. **GUID idempotency**: The GUID `"radar-" + sha1(YYYY-MM-DD)[:12]` must remain deterministic.
   Any new stage that produces output must check the GUID before writing.
3. **Config-first**: Any new tunable value must live in `pipeline/config.yaml` and be overridable
   via `RADAR_KEY__SUBKEY` env var — never hard-code thresholds or weights in module code.

## Adding a new pipeline stage

### 1. Create the module

```python
# pipeline/my_stage.py
import logging
log = logging.getLogger(__name__)

def run(previous_output) -> SomeResult:
    """One-line description of what this stage does."""
    ...
```

### 2. Add to `pipeline/main.py`

Insert the stage call at the correct index in `run_full()`. Keep stage ordering comment up to date:
```python
# Stage N: My Stage
log.info("--- Stage N: My Stage ---")
result = my_stage.run(previous)
```

### 3. Add config values

In `pipeline/config.yaml`, add under the appropriate section:
```yaml
my_stage:
  some_threshold: 0.5   # overridable via RADAR_MY_STAGE__SOME_THRESHOLD
```

Access in code:
```python
from pipeline.config import config
threshold = config.get("my_stage.some_threshold")
```

### 4. Update dependencies

Add any new package to `requirements.txt` with a minimum version:
```
some-package>=1.2.0
```

### 5. Update documentation

Update `.github/copilot-instructions.md` → **Module Responsibilities** table with the new module.

## Adding a new scoring dimension

Current weights (in `pipeline/config.yaml`):
```yaml
weights:
  growth: 0.35      # RADAR_WEIGHTS__GROWTH
  health: 0.25
  quality: 0.20
  adoption: 0.20
```

To add a new dimension:
1. Add a field to `pipeline/models.py` → `RepoScore` dataclass
2. Add weight to `config.yaml` (and reduce another weight so total stays 1.0)
3. Implement the signal fetch in `pipeline/discover.py` → `_score_repo()`
4. Update classification thresholds in `config.yaml` → `thresholds` section if needed

## Adding a new TTS provider

Current chain: `edge-tts` (primary) → `gTTS` (fallback)

In `pipeline/tts.py`:
1. Add a new `_synthesise_<provider>()` async function following the `_synthesise_edge()` pattern
2. Catch the provider-specific exception and set it as the fallback trigger in `synthesise()`
3. Keep chunking at `_CHUNK_SIZE = 4800` chars — all providers have input limits
4. Log a warning with provider name when falling back

> Do not add providers that require paid API keys or auth tokens beyond `GITHUB_TOKEN`.
> GitHub Models only supports chat models — do not attempt audio synthesis via it.

## Checklist

- [ ] New module created with `log = logging.getLogger(__name__)`
- [ ] Stage inserted at correct index in `main.py` (preserve release-before-feed order)
- [ ] Config values in `config.yaml` (not hard-coded)
- [ ] `requirements.txt` updated
- [ ] `copilot-instructions.md` Module Responsibilities table updated
- [ ] Log a learning: `python scripts/log_learning.py --category LRN --area pipeline ...`

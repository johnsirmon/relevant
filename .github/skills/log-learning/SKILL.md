---
name: log-learning
description: >
  Record a discovery, error, correction, or feature request to the .learnings/ self-improvement
  loop. Use this when the user says "log this", "add a learning", "record this error", or
  describes something worth capturing for future sessions.
---

# Log a Learning Entry

## When to use

| Situation | Category | File |
|-----------|----------|------|
| Unexpected failure or API error | `ERR` | `.learnings/ERRORS.md` |
| Correction, better approach, best practice | `LRN` | `.learnings/LEARNINGS.md` |
| Missing feature or capability | `FEAT` | `.learnings/FEATURE_REQUESTS.md` |

## How to log

Use the `scripts/log_learning.py` script — do not hand-edit the `.learnings/` files directly.
The promotion workflow (`promote_learnings.py`) relies on exact formatting that the script guarantees.

```bash
python scripts/log_learning.py \
  --category <ERR|LRN|FEAT> \
  --area <pipeline|tts|rss|narration|ci|config|agent|skills|other> \
  --priority <low|medium|high|critical> \
  --summary "One-line description" \
  --details "What happened, what was wrong, what is correct." \
  --action "Specific fix or next step."
```

## Examples

### Log an API error
```bash
python scripts/log_learning.py \
  --category ERR \
  --area tts \
  --priority high \
  --summary "edge-tts 7.0.x returns 403 from Microsoft endpoint" \
  --details "Microsoft updated their Bing speech endpoint. edge-tts 7.0.x hard-codes the stale URL and gets 403. Version 7.2.7 works." \
  --action "Pin edge-tts>=7.2.7 in requirements.txt"
```

### Log a best practice
```bash
python scripts/log_learning.py \
  --category LRN \
  --area pipeline \
  --priority medium \
  --summary "Use --podcast-only to re-test narration without re-running research" \
  --details "Running --podcast-only reuses cached README.md and skips discovery/research. Faster for iterating on narration and TTS." \
  --action "Document in copilot-instructions.md under Commands"
```

### Log a feature request
```bash
python scripts/log_learning.py \
  --category FEAT \
  --area rss \
  --priority low \
  --summary "Add chapter markers to podcast.xml" \
  --details "Each repo section in the episode could map to a chapter marker using the Podcast namespace spec." \
  --action "Research podcast:chapters namespace and add to feed.py"
```

## What happens next

Entries with `**Status**: pending` are automatically reviewed and promoted to
`copilot-instructions.md` by the **🧠 Self-Improve** GitHub Actions workflow.  
Trigger it manually from the Actions tab, or it runs automatically when `.learnings/` files change.

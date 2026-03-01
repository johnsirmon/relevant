# Product Requirements Document (PRD)

## Product Name
Weekly Developer Radar Podcast

## Problem Statement
Developer tooling in the AI agent ecosystem changes weekly, and high-signal changes are buried across many repositories and discussions. The product must produce a reliable weekly intelligence briefing and publish it as a podcast episode with minimal manual intervention.

## Target User
Experienced developers who already use AI-assisted tooling (for example GitHub Copilot Chat, VS Code Insiders, and Claude Code) and want actionable updates on what actually changed, what matters, and what workflows are now better.

## Objectives
1. Identify fast-rising open-source repositories in selected topics every week.
2. Produce a concise but deep written briefing of notable changes from the last 7 days.
3. Convert the briefing into a narration-friendly script and then to audio.
4. Publish each episode via RSS with stable hosting and duplicate protection.
5. Support dry-run validation and low-friction triggering from GitHub workflows/mobile.

## Scope

### In Scope
1. Weekly repo discovery and ranking by configurable indicators.
2. Top-5 deep-dive research for weekly change analysis.
3. Markdown briefing generation.
4. Script transformation for spoken delivery.
5. TTS generation with primary/fallback providers.
6. RSS feed update with dedupe and episode metadata.
7. Hosted MP3 publication via GitHub Release assets.
8. GitHub Actions automation.

### Out of Scope
1. Manual curation UI.
2. Listener analytics dashboards.
3. Multi-language narration.
4. Human voice recording workflows.
5. Historical backfill guarantees for old episodes.

## Default Inputs and Configuration

### Default Topic List (Configurable)
1. AI Agents
2. GitHub Copilot
3. Copilot CLI
4. Claude Code
5. Model Context Protocol

### Discovery Window and Selection
1. Time window: last 7 days.
2. Repository type: open source only.
3. Selection size: top 5 repositories for deep dive.

### Execution Controls
1. Full pipeline mode: `--podcast` or `PUBLISH_PODCAST=1`.
2. Podcast-only mode: `--podcast-only` (reuse existing `README.md`).
3. Dry-run mode: update feed with placeholders, skip real audio synthesis.

## Ranking and Health Model

### Indicator Categories and Default Weights
1. Growth Momentum (35%)
2. Maintenance Health (25%)
3. Engineering Quality (20%)
4. Adoption Signals (20%)

### Default Indicator Set
1. Growth Momentum: star velocity, fork growth, acceleration trend.
2. Maintenance Health: recent commits, release cadence, active contributors, issue responsiveness.
3. Engineering Quality: CI/CD presence, tests, modular structure, dependency freshness.
4. Adoption Signals: package downloads, ecosystem integrations, community activity.

### Status Classification Labels
1. Rising & Healthy
2. Mature & Stable
3. Hype-Driven
4. Niche but Strong
5. At Risk

### Scoring Notes
1. Default weights above are the system default and must be configurable.
2. Thresholds for status classes are configurable and should be externally tunable.
3. Weekly output must include both numeric score and status class for each analyzed repository.

## Functional Requirements

### FR-1: Weekly Discovery
1. System ingests configured topic list.
2. System identifies candidate repositories for last-7-day activity.
3. System ranks candidates with configurable weighted indicators.
4. System selects top 5 repositories for deep analysis.

### FR-2: Weekly Change Research Agent
1. Agent analyzes what changed in each selected repository over the last week.
2. Agent highlights changes relevant to developer productivity and agent workflows.
3. Agent emphasizes practical implications and better approaches when detected.

### FR-3: Written Briefing Output
1. Generate a weekly markdown briefing (`README.md`) with narrative sections.
2. Include per-repo summaries, key deltas, implications, and recommendation notes.
3. Content should assume technical literacy and avoid beginner-oriented explanations.

### FR-4: Narration Script Generation
1. Convert briefing markdown to spoken script via `narrate.py`.
2. Remove visual-only content (tables, TOC, link-heavy metadata).
3. Preserve story-style flow and section transitions.
4. Add a consistent intro and outro template for voice continuity.
5. Optionally include cold open and closing derived from the research report.

### FR-5: One-Hour Episode Target
1. Primary success measure is generated audio duration, target `60 +/- 5` minutes.
2. Script generation may use text-length heuristics, but final pass/fail is audio runtime.
3. If runtime is outside tolerance, pipeline should support optional script expansion/compression pass.

### FR-6: Text-to-Speech and Fallback
1. Generate `radar.mp3` from narration script.
2. Primary provider: `edge-tts`.
3. Fallback provider: OpenAI TTS through GitHub Models using `GITHUB_TOKEN`.
4. If primary fails, fallback is attempted automatically in the same run.

### FR-7: Episode Metadata and Feed Update
1. Build episode record with: `title`, `guid`, `pub_date`, `mp3_url`, `file_size_bytes`.
2. Prepend episode into `podcast.xml` using valid RSS 2.0 with iTunes tags.
3. Deduplicate by `guid` to prevent duplicate episodes across reruns.

### FR-8: Hosting and Distribution
1. Publish MP3 to a stable URL (GitHub Release asset URL).
2. Commit updated `README.md` and `podcast.xml`.
3. Subscribers must receive new episodes via RSS feed update.

### FR-9: Dry-Run Behavior
1. Dry-run skips real TTS generation and MP3 upload.
2. Dry-run still updates `podcast.xml` with placeholder episode metadata.
3. Placeholder enclosure URL must be deterministic and clearly marked non-production.
4. Goal is fastest/easiest validation path for workflow checks.

### FR-10: GitHub Automation
1. Workflow `update-radar.yml` runs `python -m pipeline.main`.
2. Workflow commits changed artifacts.
3. If `radar.mp3` exists, workflow creates or updates dated GitHub Release for hosting.
4. Workflow must be invocable through `workflow_dispatch` to support GitHub mobile triggering.

## Non-Functional Requirements
1. Implementation language may be Python; no language lock beyond operational reliability.
2. Pipeline should be idempotent for reruns on same input window.
3. Feed output must remain valid XML and podcast-client compatible.
4. Failure handling must be explicit and observable in logs.
5. Weekly execution should complete without manual editing in the common path.

## Data Contracts

### Core Artifacts
1. Research briefing: `README.md`.
2. Narration script: intermediate output from `narrate.py`.
3. Audio file: `radar.mp3`.
4. Feed: `podcast.xml`.

### Episode Record Schema
1. `title`: string.
2. `guid`: unique stable identifier.
3. `pub_date`: RFC 2822 compatible date string.
4. `mp3_url`: absolute URL to hosted audio.
5. `file_size_bytes`: integer.

## End-to-End Pipeline
1. Discover repositories from configured topics and time window.
2. Score, classify, and select top 5.
3. Run weekly change research and produce markdown briefing.
4. Convert briefing to narration script.
5. Generate audio with primary/fallback TTS.
6. Publish or stage episode metadata.
7. Prepend deduped episode in `podcast.xml`.
8. Commit artifacts and publish release-hosted MP3 URL.

## Acceptance Criteria

### AC-1 Discovery and Ranking
1. For a weekly run, system outputs ranked candidates and selected top 5.
2. Each selected repo includes indicator scores, weighted total, and classification label.

### AC-2 Research Output
1. Generated `README.md` includes weekly delta analysis for each of top 5.
2. Content includes practical implications for developer workflows.

### AC-3 Script Conversion
1. Narration script excludes tables/TOC/link metadata noise.
2. Intro/outro are present and consistent across episodes.

### AC-4 Audio Generation
1. `radar.mp3` is generated when not in dry-run.
2. On primary TTS failure, fallback path is attempted automatically.
3. Runtime target for episode is `60 +/- 5` minutes.

### AC-5 Feed and Publish
1. New episode appears at top of `podcast.xml`.
2. Duplicate `guid` is not inserted.
3. RSS remains valid and includes expected iTunes fields.
4. Hosted MP3 URL resolves when real audio is generated.

### AC-6 Dry-Run
1. No real TTS call is required.
2. Feed is updated with placeholder episode record for pipeline validation.
3. Run can be triggered via GitHub Actions manual dispatch suitable for GitHub mobile use.

## Risks and Mitigations
1. API rate limiting on upstream sources.
  Mitigation: retries, backoff, and cached intermediate results.
2. False positives in trend detection.
  Mitigation: weighted model tuning and threshold calibration.
3. TTS provider instability.
  Mitigation: automatic provider fallback and clear error reporting.
4. Feed corruption from malformed updates.
  Mitigation: XML validation and guid-based idempotency checks.

## Open Decisions
1. Exact numeric thresholds for status categories.
2. Preferred placeholder URL policy for dry-run environments.
3. Optional auto-adjust loop strategy when duration misses target band.

## Implementation Mapping (Current Code Layout)
1. `main.py` orchestrates full pipeline and mode selection.
2. `narrate.py` converts markdown into narration-ready script.
3. `tts.py` handles primary and fallback TTS synthesis.
4. `podcast.py` writes deduped RSS updates.
5. `update-radar.yml` automates execution and publication.

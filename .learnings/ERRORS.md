# Errors

Unexpected failures, API issues, and debugging discoveries captured during sessions.

<!-- Format: append entries below. Run the promote-learnings workflow to graduate recurring errors into copilot-instructions.md -->

## 2026-03-01 — GitHub Models has no TTS endpoint

**Symptom:** `openai.BadRequestError: Unknown model: tts-1-hd` when calling `https://models.inference.ai.azure.com/audio/speech`  
**Root cause:** GitHub Models only proxies *chat* models (`gpt-4o`, `gpt-4o-mini`, etc.). The `/audio/speech` endpoint does not exist on that proxy.  
**Fix:** Replace OpenAI TTS fallback with `gTTS` (Google TTS, free, no auth). The `openai` package is still used for the research summarisation step via GitHub Models chat endpoint.  
**Lesson:** Do not assume GitHub Models mirrors the full OpenAI API surface — verify endpoint availability before using non-chat features.

## 2026-03-01 — edge-tts 7.0.x returns 403

**Symptom:** `edge-tts` synthesis fails with HTTP 403.  
**Root cause:** Microsoft updated their Bing speech endpoint; older `edge-tts` builds hard-code the stale URL.  
**Fix:** Pin `edge-tts>=7.2.7` in `requirements.txt`.

## 2026-03-01 — ffmpeg not on PATH after winget install (Windows)

**Symptom:** `FileNotFoundError: [WinError 2] The system cannot find the file specified` when calling ffmpeg.  
**Root cause:** winget installs to an AppData path that is NOT automatically added to the current shell's `PATH`. A new terminal is required, or `$env:PATH` must be manually updated.  
**Fix:** Open a new terminal after `winget install Gyan.FFmpeg`, or set `$env:PATH` explicitly in-session:  
```powershell
$env:PATH = "C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\bin;$env:PATH"
```

## 2026-03-01 — mistune 3.x API incompatible with 2.x renderer pattern

**Symptom:** `AttributeError: 'RadarRenderer' object has no attribute 'render_children'`  
**Root cause:** mistune 3.x removed `render_children()`; use `self.render_tokens(token.get('children', []), state)` instead. Also adds a `block_text` token type wrapping inline content inside list items.  
**Fix:** Add `_children()` helper method; add explicit `block_text` handler returning `self.render_token(token, state)` for children.


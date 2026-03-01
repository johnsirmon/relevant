"""TTS synthesis: edge-tts primary, OpenAI via GitHub Models fallback."""
import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import mutagen.mp3
from openai import OpenAI

log = logging.getLogger(__name__)

_OUTPUT = Path("radar.mp3")
_EDGE_VOICE = "en-US-AriaNeural"
_OPENAI_VOICE = "alloy"
_OPENAI_MODEL = "tts-1-hd"
_OPENAI_BASE_URL = "https://models.inference.ai.azure.com"

# Max chars edge-tts handles reliably in one shot
_CHUNK_SIZE = 4800


def _split_script(script: str) -> list[str]:
    """Split on paragraph boundaries to stay under edge-tts limits."""
    paragraphs = script.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > _CHUNK_SIZE:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para).strip()
    if current:
        chunks.append(current.strip())
    return chunks


async def _edge_tts_chunk(text: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, _EDGE_VOICE)
    await communicate.save(str(out_path))


def _synthesise_edge(script: str, output: Path) -> None:
    """Synthesise via edge-tts, concatenating chunks."""
    chunks = _split_script(script)
    log.info("edge-tts: synthesising %d chunk(s)", len(chunks))

    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, chunk in enumerate(chunks):
            part = Path(tmp) / f"part_{i:04d}.mp3"
            asyncio.run(_edge_tts_chunk(chunk, part))
            parts.append(str(part))

        if len(parts) == 1:
            Path(parts[0]).rename(output)
        else:
            _concat_mp3(parts, output)


def _concat_mp3(parts: list[str], output: Path) -> None:
    """Concatenate MP3 files using ffmpeg."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lst:
        for p in parts:
            lst.write(f"file '{p}'\n")
        lst_path = lst.name
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst_path, "-c", "copy", str(output)],
        check=True, capture_output=True,
    )
    Path(lst_path).unlink(missing_ok=True)


def _synthesise_openai(script: str, output: Path) -> None:
    """Synthesise via OpenAI TTS through GitHub Models."""
    log.info("OpenAI TTS fallback: synthesising %d chars", len(script))
    client = OpenAI(base_url=_OPENAI_BASE_URL, api_key=os.environ["GITHUB_TOKEN"])

    # OpenAI TTS has a 4096-char limit per request — chunk and concatenate
    chunks = _split_script(script)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, chunk in enumerate(chunks):
            part = Path(tmp) / f"part_{i:04d}.mp3"
            response = client.audio.speech.create(
                model=_OPENAI_MODEL, voice=_OPENAI_VOICE, input=chunk
            )
            part.write_bytes(response.content)
            parts.append(str(part))

        if len(parts) == 1:
            Path(parts[0]).rename(output)
        else:
            _concat_mp3(parts, output)


def get_duration_seconds(mp3_path: Path) -> int:
    audio = mutagen.mp3.MP3(str(mp3_path))
    return int(audio.info.length)


def _adjust_tempo(mp3_path: Path, target_min: int, target_max: int) -> None:
    """Use ffmpeg atempo filter to nudge audio into target duration range."""
    duration = get_duration_seconds(mp3_path)
    target_mid = (target_min + target_max) / 2 * 60  # seconds
    ratio = round(duration / target_mid, 4)
    ratio = max(0.9, min(1.1, ratio))  # clamp to ±10%

    if abs(ratio - 1.0) < 0.01:
        log.info("Duration %.1fs within tolerance, no adjustment needed", duration)
        return

    log.info("Adjusting tempo by %.3f (duration %ds → target %ds)", ratio, duration, int(target_mid))
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path), "-filter:a", f"atempo={ratio}", tmp_path],
        check=True, capture_output=True,
    )
    Path(tmp_path).replace(mp3_path)


def synthesise(
    script: str,
    output: Path = _OUTPUT,
    auto_adjust: bool = False,
    target_min_min: int = 55,
    target_max_min: int = 65,
) -> Path:
    """
    Synthesise script to MP3. Tries edge-tts first; falls back to OpenAI TTS.
    Validates duration against target range. Optionally adjusts tempo.
    Returns path to output MP3.
    """
    # Primary
    try:
        _synthesise_edge(script, output)
        log.info("edge-tts synthesis complete: %s", output)
    except Exception as exc:
        log.warning("edge-tts failed (%s), trying OpenAI fallback", exc)
        _synthesise_openai(script, output)
        log.info("OpenAI TTS synthesis complete: %s", output)

    duration = get_duration_seconds(output)
    log.info("Audio duration: %ds (%.1f min)", duration, duration / 60)

    if auto_adjust:
        _adjust_tempo(output, target_min_min, target_max_min)
        duration = get_duration_seconds(output)
        log.info("Post-adjust duration: %ds (%.1f min)", duration, duration / 60)

    min_s, max_s = target_min_min * 60, target_max_min * 60
    if not (min_s <= duration <= max_s):
        log.warning(
            "Audio duration %ds is outside target %d–%d min",
            duration, target_min_min, target_max_min,
        )
    else:
        log.info("Duration check passed ✓")

    return output

#!/usr/bin/env python3
"""Fetch a timestamped transcript + metadata for a YouTube video via yt-dlp.

Prints a markdown report (metadata, chapters, transcript location) to stdout
and writes the transcript itself — one `[MM:SS] text` block per line — to a
file the caller Reads in slices.

Sub-track selection: native captions in the video's language first, then
auto-generated captions, then English auto-translate as a last resort (the
report flags machine translation). No audio is downloaded, ever.

Dedup handles the two ways YouTube auto-subs actually misbehave: consecutive
identical cues (rolling repeats) and prefix-extension cues ("so the thing" →
"so the thing about markets"). It never drops a legitimately repeated line
from elsewhere in the video.

Exit codes: 0 ok · 2 metadata/download failure · 3 no subtitles available.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TS_RE = re.compile(
    r"(\d{2,}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2,}):(\d{2}):(\d{2})[.,](\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")

# Coalescing knobs: cues merge into one stamped block until it holds this many
# words, or a silence gap this long splits it (chapter/topic boundaries).
BLOCK_WORDS = 45
GAP_SPLIT_S = 4.0


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def stamp(seconds: float) -> str:
    t = int(seconds)
    if t >= 3600:
        return f"[{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}]"
    return f"[{t // 60:02d}:{t % 60:02d}]"


def parse_vtt(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    segments: list[dict] = []
    prev_cue: list[str] = []
    i = 0
    while i < len(lines):
        match = TS_RE.match(lines[i])
        if not match:
            i += 1
            continue
        start = _to_seconds(*match.groups()[:4])
        end = _to_seconds(*match.groups()[4:])
        i += 1
        cue: list[str] = []
        while i < len(lines) and lines[i].strip():
            cleaned = TAG_RE.sub("", lines[i]).strip()
            if cleaned:
                cue.append(cleaned)
            i += 1
        # YouTube rolling window: each cue re-shows lines from the previous
        # cue. Emit only the lines this cue introduces.
        fresh = [l for l in cue if l not in prev_cue]
        prev_cue = cue
        text = " ".join(fresh).strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})
        i += 1
    return dedupe(segments)


def dedupe(segments: list[dict]) -> list[dict]:
    out: list[dict] = []
    for seg in segments:
        if out and seg["text"] == out[-1]["text"]:
            out[-1]["end"] = seg["end"]
            continue
        if out and seg["text"].startswith(out[-1]["text"] + " "):
            out[-1]["text"] = seg["text"]
            out[-1]["end"] = seg["end"]
            continue
        out.append(seg)
    return out


def coalesce(segments: list[dict]) -> list[dict]:
    """Merge short cues into ~sentence-sized blocks, one timestamp each."""
    blocks: list[dict] = []
    for seg in segments:
        if blocks:
            cur = blocks[-1]
            gap = seg["start"] - cur["end"]
            if gap < GAP_SPLIT_S and len(cur["text"].split()) < BLOCK_WORDS:
                cur["text"] += " " + seg["text"]
                cur["end"] = seg["end"]
                continue
        blocks.append(dict(seg))
    return blocks


def fetch_info(url: str) -> dict:
    proc = subprocess.run(
        ["yt-dlp", "--no-warnings", "--skip-download", "-J", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(2)
    return json.loads(proc.stdout)


def base(code: str) -> str:
    return code.split("-")[0].lower()


def match_lang(tracks: dict, lang: str) -> str | None:
    """Match a language code against track keys, region-insensitively.

    'en-US' matches keys 'en-US', 'en', or 'en-GB' — exact key first,
    then the bare base code, then any regioned variant of the same base.
    """
    if lang in tracks:
        return lang
    if base(lang) in tracks:
        return base(lang)
    for key in tracks:
        if base(key) == base(lang):
            return key
    return None


def choose_track(info: dict, lang: str) -> tuple[str, str, bool] | None:
    """Return (lang_key, source_label, machine_translated) or None."""
    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}
    key = match_lang(subs, lang)
    if key:
        return key, f"native captions ({key})", False
    key = match_lang(autos, lang) or match_lang(autos, base(lang) + "-orig")
    if key:
        return key, f"auto-generated captions ({key})", False
    key = match_lang(autos, "en")
    if key:
        return key, f"auto-translated to English from {lang} (machine-translated — nuance may be off)", True
    return None


def download_subs(url: str, lang_key: str, out_dir: Path) -> Path:
    proc = subprocess.run(
        [
            "yt-dlp", "--no-warnings", "--skip-download",
            "--write-subs", "--write-auto-subs",
            "--sub-langs", lang_key, "--sub-format", "vtt/best",
            "-o", str(out_dir / "sub.%(ext)s"), url,
        ],
        capture_output=True, text=True,
    )
    files = sorted(out_dir.glob("sub.*.vtt")) or sorted(out_dir.glob("sub.*"))
    if not files:
        print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(2)
    return files[0]


def main() -> int:
    ap = argparse.ArgumentParser(prog="fetch_transcript")
    ap.add_argument("url", help="YouTube video URL")
    ap.add_argument("--lang", default=None, help="Preferred transcript language (default: video language)")
    ap.add_argument("--out-dir", default=None, help="Working directory (default: tmp)")
    args = ap.parse_args()

    info = fetch_info(args.url)
    lang = args.lang or info.get("language") or "en"

    track = choose_track(info, lang)
    duration = int(info.get("duration") or 0)
    print(f"# {info.get('title', '?')}")
    print(f"- Channel: {info.get('uploader') or info.get('channel', '?')}")
    print(f"- Duration: {info.get('duration_string', '?')} ({duration}s)")
    print(f"- Video language: {info.get('language') or 'unknown'}")
    print(f"- Upload date: {info.get('upload_date', '?')}")
    print(f"- URL: {info.get('webpage_url', args.url)}")

    if track is None:
        print("\nNo subtitles available in any usable language — transcript cannot be fetched.")
        return 3
    lang_key, source, translated = track
    print(f"- Transcript source: {source}")

    out_dir = Path(args.out_dir) if args.out_dir else Path(
        tempfile.mkdtemp(prefix="watch-or-skip-")
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # Slim metadata cache for probe_format.py (storyboard grid + duration).
    slim = {k: info.get(k) for k in (
        "id", "title", "uploader", "channel", "duration", "duration_string",
        "language", "upload_date", "webpage_url", "chapters",
    )}
    slim["storyboards"] = [
        f for f in (info.get("formats") or []) if f.get("format_id", "").startswith("sb")
    ]
    (out_dir / "info.json").write_text(json.dumps(slim), encoding="utf-8")

    vtt = download_subs(args.url, lang_key, out_dir)
    blocks = coalesce(parse_vtt(vtt))
    if not blocks:
        print("\nSubtitle file downloaded but produced an empty transcript.")
        return 3

    transcript = out_dir / "transcript.txt"
    transcript.write_text(
        "\n".join(f"{stamp(b['start'])} {b['text']}" for b in blocks) + "\n",
        encoding="utf-8",
    )

    chapters = info.get("chapters") or []
    if chapters:
        print("\n## Chapters")
        for ch in chapters:
            t = int(ch.get("start_time") or 0)
            print(f"{stamp(t)} {ch.get('title', '?')} (t={t}s)")

    desc = (info.get("description") or "").strip()
    if desc:
        print("\n## Description (truncated)")
        print(desc[:800])

    words = sum(len(b["text"].split()) for b in blocks)
    print("\n## Transcript")
    print(f"Path: {transcript}")
    print(f"Blocks: {len(blocks)} · ~{words} words · stamps are [MM:SS] "
          f"(or [H:MM:SS] past the hour) — convert to seconds for &t=Ns links")
    print(f"Coverage: {stamp(blocks[0]['start'])} → {stamp(blocks[-1]['end'])} "
          f"of {info.get('duration_string', '?')} runtime")
    if translated:
        print("Note: machine-translated — flag this in the review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

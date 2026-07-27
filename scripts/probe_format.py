#!/usr/bin/env python3
"""Screen-dependence probe: sample YouTube storyboard sheets (no video download).

Storyboards are the pre-rendered thumbnail mosaics YouTube serves for the
seek-bar preview — a few hundred KB for a whole video. Each sheet is a
rows×columns grid of frames in row-major order at a fixed time interval.
Reading 2-3 sheets is enough to classify the format (talking heads / slides /
screen-share / b-roll) and decide whether the video needs the screen or works
as background audio.

Reads info.json cached by fetch_transcript.py in the same directory (falls
back to fetching metadata itself when --url is given without a cache).

Exit codes: 0 ok · 2 download/metadata failure · 3 no storyboards available.
"""
from __future__ import annotations

import argparse
import email
import json
import subprocess
import sys
from pathlib import Path


def stamp(seconds: float) -> str:
    t = int(seconds)
    if t >= 3600:
        return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"
    return f"{t // 60:02d}:{t % 60:02d}"


def load_info(out_dir: Path, url: str | None) -> dict:
    cache = out_dir / "info.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if not url:
        print("No info.json in --dir and no --url given.", file=sys.stderr)
        raise SystemExit(2)
    proc = subprocess.run(
        ["yt-dlp", "--no-warnings", "--skip-download", "-J", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(2)
    info = json.loads(proc.stdout)
    info["storyboards"] = [
        f for f in (info.get("formats") or []) if f.get("format_id", "").startswith("sb")
    ]
    return info


def pick_board(info: dict) -> dict | None:
    boards = info.get("storyboards") or []
    if not boards:
        return None
    # Largest tile size = most readable; sb0 by YouTube convention.
    return max(boards, key=lambda f: (f.get("width") or 0))


def auto_sheet_count(duration: float) -> int:
    """One sheet per ~25 min of runtime, floor 3, cap 6."""
    return max(3, min(6, round(duration / 1500)))


def pick_indices(total: int, n: int) -> list[int]:
    """n interior positions across [0, total): midpoints of n equal strata.

    Avoids the first/last sheet on long videos, where intro montages and
    outro cards live — the middle of the video is what classifies format.
    """
    if n >= total:
        return list(range(total))
    return sorted({int((i + 0.5) / n * total) for i in range(n)})


def extract_sheets(mhtml: Path, out_dir: Path) -> list[Path]:
    msg = email.message_from_bytes(mhtml.read_bytes())
    sheets: list[Path] = []
    for part in msg.walk():
        if part.get_content_type() == "image/jpeg":
            p = out_dir / f"sheet{len(sheets):03d}.jpg"
            p.write_bytes(part.get_payload(decode=True))
            sheets.append(p)
    return sheets


def main() -> int:
    ap = argparse.ArgumentParser(prog="probe_format")
    ap.add_argument("--dir", required=True, help="Working dir (from fetch_transcript.py)")
    ap.add_argument("--url", default=None, help="Video URL (optional if info.json is cached)")
    ap.add_argument("--sheets", type=int, default=None,
                    help="How many sheets to sample (default: scales with duration, 3-6)")
    args = ap.parse_args()

    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = load_info(out_dir, args.url)
    url = args.url or info.get("webpage_url")

    board = pick_board(info)
    if board is None:
        print("No storyboards available for this video — probe not possible. "
              "Fall back to judging screen-dependence from transcript cues.")
        return 3

    proc = subprocess.run(
        ["yt-dlp", "--no-warnings", "-f", board["format_id"],
         "-o", str(out_dir / "storyboard.%(ext)s"), url],
        capture_output=True, text=True,
    )
    mhtml = out_dir / "storyboard.mhtml"
    if proc.returncode != 0 or not mhtml.exists():
        print(proc.stderr.strip(), file=sys.stderr)
        return 2

    sheets = extract_sheets(mhtml, out_dir)
    if not sheets:
        print("Storyboard downloaded but no images found inside.", file=sys.stderr)
        return 2

    rows, cols = board.get("rows") or 1, board.get("columns") or 1
    fps = board.get("fps") or 0
    interval = 1 / fps if fps else 0
    per_sheet = rows * cols
    duration = info.get("duration") or 0

    n = args.sheets or auto_sheet_count(duration)
    picked = pick_indices(len(sheets), n)

    print(f"# Format probe — {len(picked)} of {len(sheets)} storyboard sheets")
    print(f"Grid: {rows}x{cols} per sheet, row-major, one frame every ~{interval:.0f}s")
    print("Read each sheet below; classify the format "
          "(talking heads / slides / screen-share / chart / b-roll):")
    for k in picked:
        lo = k * per_sheet * interval
        hi = min(duration, (k + 1) * per_sheet * interval) if duration else (k + 1) * per_sheet * interval
        print(f"- {sheets[k]}  covers [{stamp(lo)}-{stamp(hi)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Parser unit tests — no network. Run: python3 -m pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_transcript import coalesce, dedupe, parse_vtt, stamp
from probe_format import auto_sheet_count, pick_indices


def _vtt(tmp_path, body):
    p = tmp_path / "sub.en.vtt"
    p.write_text("WEBVTT\n\n" + body, encoding="utf-8")
    return p


def test_parse_strips_tags_and_keeps_stamps(tmp_path):
    segs = parse_vtt(_vtt(tmp_path, (
        "00:00:01.000 --> 00:00:03.000\n<c>hello</c> world\n\n"
        "00:00:03.000 --> 00:00:05.000\nsecond cue\n"
    )))
    assert [s["text"] for s in segs] == ["hello world", "second cue"]
    assert segs[0]["start"] == 1.0


def test_parse_drops_rolling_window_lines(tmp_path):
    segs = parse_vtt(_vtt(tmp_path, (
        "00:00:00.000 --> 00:00:02.000\nline A\nline B\n\n"
        "00:00:02.000 --> 00:00:04.000\nline B\nline C\n\n"
        "00:00:04.000 --> 00:00:06.000\nline C\nline D\n"
    )))
    assert [s["text"] for s in segs] == ["line A line B", "line C", "line D"]


def test_dedupe_merges_rolling_and_prefix_extension():
    segs = [
        {"start": 0, "end": 2, "text": "so the thing"},
        {"start": 2, "end": 4, "text": "so the thing"},
        {"start": 4, "end": 6, "text": "so the thing about markets"},
    ]
    out = dedupe(segs)
    assert len(out) == 1
    assert out[0]["text"] == "so the thing about markets"
    assert out[0]["end"] == 6


def test_dedupe_keeps_legit_repeats_elsewhere():
    segs = [
        {"start": 0, "end": 2, "text": "buy low"},
        {"start": 10, "end": 12, "text": "sell high"},
        {"start": 20, "end": 22, "text": "buy low"},
    ]
    assert len(dedupe(segs)) == 3


def test_coalesce_splits_on_gap():
    segs = [
        {"start": 0, "end": 2, "text": "one"},
        {"start": 2.5, "end": 4, "text": "two"},
        {"start": 20, "end": 22, "text": "after a long pause"},
    ]
    blocks = coalesce(segs)
    assert len(blocks) == 2
    assert blocks[0]["text"] == "one two"
    assert blocks[1]["start"] == 20


def test_coalesce_splits_on_word_budget():
    segs = [
        {"start": i, "end": i + 1, "text": "word " * 20} for i in range(6)
    ]
    blocks = coalesce(segs)
    assert len(blocks) > 1


def test_stamp_formats():
    assert stamp(75) == "[01:15]"
    assert stamp(4245) == "[1:10:45]"


def test_auto_sheet_count_scales_with_duration():
    assert auto_sheet_count(967) == 3       # 16 min
    assert auto_sheet_count(5400) == 4      # 90 min
    assert auto_sheet_count(7200) == 5      # 2 h
    assert auto_sheet_count(20000) == 6     # capped


def test_pick_indices_avoids_endpoints():
    picked = pick_indices(81, 5)
    assert len(picked) == 5
    assert 0 not in picked and 80 not in picked
    assert picked == sorted(picked)


def test_pick_indices_small_totals():
    assert pick_indices(2, 3) == [0, 1]
    assert pick_indices(11, 3) == [1, 5, 9]

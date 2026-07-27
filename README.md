# Watch or Skip YouTube video skill

Check if a podcast, interview, or talk on YouTube is worth watching — or skip it.

The skill fetches a **timestamped transcript** with [yt-dlp](https://github.com/yt-dlp/yt-dlp),
probes the **visual format** from YouTube storyboard thumbnails (a few hundred KB —
the video itself is never downloaded), and judges the content against a values
constitution (durable, relevant, deep, honest, correct), calibrated to a reader
profile in `~/.watch-or-skip/reader.md`.

## What's in v2

- `scripts/fetch_transcript.py` — metadata + chapters + a `[MM:SS]`-stamped
  transcript. Correct rolling-window dedup for YouTube auto-subs; native
  captions → auto-generated → English auto-translate fallback (flagged).
  Every timecode link in a review is grounded in a real stamp, not estimated.
- `scripts/probe_format.py` — samples 2-3 storyboard mosaic sheets so the
  review can say "talking heads — fine as background audio" vs "slides carry
  the data — needs the screen" (~2k image tokens, no ffmpeg, no video download).
- `references/exemplars.md` — voice exemplars, loaded only on the first run;
  after that, your own run history anchors the voice.
- `tests/` — parser unit tests (`python3 -m pytest -q`, no network).

## Installation

Install with [Vercel's Skills CLI](https://skills.sh):

```bash
npx skills add https://github.com/dmitriy-tkalich/watch-or-skip-skill

# Install yt-dlp
brew install yt-dlp
```

## Usage

Copy a YouTube video URL you want to analyze.

**Example:**

```
/watch-or-skip https://www.youtube.com/watch?v=0lJKucu6HJc
```

**Output:**

```md
Worth 15 min if you haven't absorbed YC canon. Skip if you've read PG essays or watched a YC talk before — you've heard 80% of this already.

Mid-2018 Sam Altman, pre-OpenAI-CEO, doing greatest-hits startup advice as a Startup School lecture. Most of it is bromide compressed into bullets. Two ideas are sharp enough to earn the 16 minutes.

*How to Succeed with a Startup* — Y Combinator, 16 min, English. Speaker + full-screen text slides; the slides only echo his points — fine as background audio.

**Real trends look like obsessive use, not high sales.** ([2 min in](https://www.youtube.com/watch?v=0lJKucu6HJc&t=120s)) iPhone in its first year sold ~1M units — but those owners used it hours a day. VR in 2018 had comparable launch-window numbers — but most headsets sat in drawers. The test isn't units sold, it's hours-per-user among early adopters.

**The hard startup is easier than the easy one.** ([4 min in](https://www.youtube.com/watch?v=0lJKucu6HJc&t=262s)) Capital is cheap, talent isn't. Getting employee 8 to leave a FAANG job for a slightly-better-CRM is brutal; getting them for a moonshot is doable.

The team-traits middle ([6 min onward](https://www.youtube.com/watch?v=0lJKucu6HJc&t=390s)) is the weakest stretch — optimist / action-bias platitudes. No sponsor reads, no intro bloat — the talk is already its own dense version.
```

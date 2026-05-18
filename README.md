# Watch or Skip YouTube video skill

Check if podcast, interview, guide on YouTube worth watching or skip it.

The skill fetches YouTube transcript with [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Installation

Install with [Vercel's Skills CLI](https://skills.sh):

```bash
npx skills add https://github.com/dmitriy-tkalich/watch-or-skip-skill

# Install yt-dlp
brew install yt-dlp
```

## Usage

Copy YouTube video URL which you want to analyze.

**Example:**

```
/watch-or-skip https://www.youtube.com/watch?v=0lJKucu6HJc
```

**Output:**

```md
---
url: https://www.youtube.com/watch?v=0lJKucu6HJc
title: Sam Altman - How to Succeed with a Startup
channel: Y Combinator
language: en
duration: 16:07
verdict: Worth 15 min if you're new to YC canon. Skip if you've read PG essays before.
---

Worth 15 min if you haven't absorbed YC canon. Skip if you've read PG essays or watched a YC talk before — you've heard 80% of this already.

Mid-2018 Sam Altman, pre-OpenAI-CEO, doing greatest-hits startup advice as a Startup School lecture. Most of it is bromide compressed into bullets. Two ideas are sharp enough to earn the 16 minutes.

**Real trends look like obsessive use, not high sales.** ([2 min in](https://www.youtube.com/watch?v=0lJKucu6HJc&t=120s)) iPhone in its first year sold ~1M units — but those owners used it hours a day. VR in 2018 had comparable launch-window numbers — but most headsets sat in drawers. The test isn't units sold, it's hours-per-user among early adopters. The 2018 VR call aged well: Vision Pro shipped, hours-per-user stayed low, his framing still picks the right side. Apply it now to "AI agents" — Cursor's daily-active hours look like iPhone-2008; most agent frameworks look like 2018 VR.

**The hard startup is easier than the easy one.** ([4 min in](https://www.youtube.com/watch?v=0lJKucu6HJc&t=262s)) Capital is cheap, talent isn't. Getting employee 8 to leave a FAANG job for a slightly-better-CRM is brutal; getting them for a moonshot is doable. Ambition flips from risk factor to recruiting tool — easy-mode startups die mid-headcount-ramp because nobody good wants to join them.

The team-traits middle ([6 min onward](https://www.youtube.com/watch?v=0lJKucu6HJc&t=390s)) is the weakest stretch — optimist / action-bias / "we'll figure it out" platitudes. The "one no vs one yes" frame [13 min in](https://www.youtube.com/watch?v=0lJKucu6HJc&t=793s) is a clean third idea: at a big co every veto kills it; at a startup one yes saves it. No sponsor reads, no intro bloat — the talk is already its own dense version.
```

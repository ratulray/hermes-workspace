---
name: twitter-feed
description: Scrape posts from your X/Twitter home feed (Following or For You tab) using agent-browser with your existing Chrome credentials. Use when asked to check Twitter, summarize the feed, show recent posts, or read what people are posting. Triggers: "check my twitter feed", "what's on my twitter", "summarize my following feed", "show me my X feed", "what did people post today".
argument-hint: 'twitter-feed, twitter-feed --tab for-you, twitter-feed --hours 48'
allowed-tools: Bash(agent-browser:*)
---

# twitter-feed — X/Twitter Feed Scraper

Scrape and summarize posts from the user's X/Twitter home feed using their existing Chrome session via `agent-browser`.

## Arguments

Parse from ARGUMENTS:
- `--tab` — `following` (default) or `for-you`
- `--hours` — how many hours back to include (default: `24`)
- `--count` — stop after this many posts (default: unlimited, stop at time boundary)

## Pre-flight Check — Verify Profile Auth State

**Always do this BEFORE proceeding.** Twitter sessions expire server-side and `state save` does not reliably persist Twitter cookies.

```bash
agent-browser close --all 2>/dev/null; sleep 1
agent-browser \
  --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com
agent-browser wait --load networkidle
agent-browser screenshot /tmp/twitter_auth_check.png
```

**If the screenshot shows a login page** (X logo on right, "Happening now" headline, email input field): re-authenticate manually first:
1. Open Chrome manually: `open -a "Google Chrome" --args --profile-directory="chrome-twitter"`
2. Log into x.com
3. Confirm the home feed loads
4. Then re-run the skill

**If the screenshot shows the home feed**: proceed with the normal workflow.

## Launch Command (Always use this exact form)

```bash
agent-browser \
  --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com/home
```

**Why these flags matter:**
- `--executable-path`: agent-browser defaults to Chrome for Testing. Regular Chrome is required for session persistence.
- `--profile ~/.openclaw/chrome-twitter`: dedicated profile with Twitter session, no Gemini side panel.
- `--disable-blink-features=AutomationControlled`: hides `navigator.webdriver`. Required to prevent Twitter from detecting and blocking the browser.

## Workflow

### Step 0 — Auth check (REQUIRED before proceeding)

```bash
agent-browser close --all 2>/dev/null; sleep 1
agent-browser \
  --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com
agent-browser wait --load networkidle
agent-browser screenshot /tmp/twitter_auth_check.png
```

### Step 1 — Open and navigate to the right tab

```bash
agent-browser \
  --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com/home
agent-browser wait --load networkidle
```

Click the correct tab:
```bash
agent-browser find role tab click --name "Following"
# or for For You:
agent-browser find role tab click --name "For you"
agent-browser wait --load networkidle
```

### Step 2 — Set viewport to a readable width

```bash
agent-browser set viewport 1440 900
```

### Step 3 — Take an initial snapshot to get tweet refs

Use `snapshot` first, before any scrolling — Gemini only opens after scroll interactions.

```bash
agent-browser snapshot
```

Parse the output for `article` elements. Each article's accessible name contains: `@handle · Nh ago [tweet text] [N replies, N reposts, N likes, N views]`.

- Tweets marked `StaticText "Ad"` are ads — skip them.
- Timestamps to watch for: `1h`, `2h`, `6h`, `23h`, `Apr 17` (date = older than 24h, stop there).

**If snapshot returns a Gemini panel** (first line is `button "Close Gemini in Chrome"`): fall back to screenshots — see Step 3b.

### Step 3b — Screenshot fallback (if Gemini hijacked the snapshot)

```bash
agent-browser screenshot /tmp/twitter_feed_1.png
```

Read each screenshot image to extract post content visually. Twitter is always on the left; Gemini side panel (if present) does not obscure the feed.

### Step 4 — Scroll and collect more posts

**Do not chain `scroll && screenshot`** in a single command — the daemon needs a moment between commands or it returns `os error 35` (resource busy). Run each separately:

```bash
agent-browser scroll down 800
agent-browser screenshot /tmp/twitter_feed_2.png
agent-browser scroll down 800
agent-browser screenshot /tmp/twitter_feed_3.png
# ... continue until timestamps exceed --hours window
```

Stop when posts exceed the requested `--hours` window.

### Step 5 — Expand truncated posts (optional)

If a tweet has `button "Show more"`, click it:
```bash
agent-browser click @eNN
```

### Step 6 — Close the browser

```bash
agent-browser close
```

## Output Format

Present results as a feed summary:

```
**@handle** · Nh ago
> [tweet text]
N replies · N reposts · N likes · NK views
[note if reposted by someone, or if it's a reply/quote tweet]

---
```

Group by theme if there are many posts. Skip ads. Note if any posts were truncated.

End with a one-line thematic summary: e.g. "Your feed today is dominated by AI agent tooling discussions."

## Known Issues

| Issue | Workaround |
|---|---|
| Gemini side panel auto-opens on scroll | Switch from `snapshot` to `screenshot` |
| Daemon busy errors (`os error 35`) | Don't chain scroll && screenshot; run separately |
| Chrome for Testing used instead of regular Chrome | Always specify `--executable-path` |
| Auth state doesn't persist | Don't use `state save/load` for Twitter; use `--profile` |
| Session invalidated server-side | Re-authenticate manually in Chrome |

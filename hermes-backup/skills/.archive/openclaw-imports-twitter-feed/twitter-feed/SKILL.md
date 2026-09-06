---
name: twitter-feed
description: Scrape posts from your X/Twitter home feed (Following or For You tab) using agent-browser with your existing Chrome credentials. Use when asked to check Twitter, summarize the feed, show recent posts, or read what people are posting. Triggers include "check my twitter feed", "what's on my twitter", "summarize my following feed", "show me my X feed", "what did people post today".
argument-hint: 'twitter-feed, twitter-feed --tab for-you, twitter-feed --hours 48'
allowed-tools: Bash(agent-browser:*)
---

# Twitter/X Feed Scraper

Scrape and summarize posts from the user's X/Twitter home feed using their existing Chrome session.

## Arguments

Parse from ARGUMENTS:
- `--tab` — `following` (default) or `for-you`
- `--hours` — how many hours back to include (default: `24`)
- `--count` — stop after this many posts (default: unlimited, stop at time boundary)

## Pre-flight Check — Verify Profile Auth State

Before scraping, always verify the profile is authenticated:

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

**If the screenshot shows a login page** (X logo on right, "Happening now" headline, email input field): the profile has **no active session**. The skill cannot work until you re-authenticate:

1. Open Chrome manually: `open -a "Google Chrome" --args --profile-directory="chrome-twitter"`
2. Log into x.com with your credentials
3. Confirm the home feed loads in the browser
4. Then re-run the skill

**If the screenshot shows the home feed** (posts, left sidebar): proceed with the normal workflow.

> [!warning]
> `agent-browser state save` does not reliably persist Twitter session cookies. If the profile was working before and now shows a login page, the session may have been invalidated server-side (account security, password change, Twitter session expiry). Re-authenticate manually.

## Launch Command (ALWAYS use this exact form)

```bash
agent-browser \
  --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com/home
```

**Why these flags matter — do not omit them:**
- `--executable-path`: agent-browser defaults to Chrome for Testing. Regular Chrome is required.
- `--profile ~/.openclaw/chrome-twitter`: dedicated profile with Twitter session, no Gemini side panel, no extensions.
- `--disable-blink-features=AutomationControlled`: hides Chrome's automation signals (`navigator.webdriver`). Required to prevent Twitter from detecting and blocking the browser.

See [references/chrome-quirks.md](references/chrome-quirks.md) for full detail on these issues.

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

If login page → re-authenticate manually first. If home feed → proceed.

### Step 1 — Open and navigate to the right tab

```bash
agent-browser --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile ~/.openclaw/chrome-twitter \
  --args "--disable-blink-features=AutomationControlled" \
  open https://x.com/home
agent-browser wait --load networkidle
```

Then click the correct tab (default: Following):
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

Use `snapshot` first, before any scrolling — Gemini only opens after scroll interactions. This is the fastest way to read the first viewport of tweet text directly.

```bash
agent-browser snapshot
```

Parse the output for `article` elements. Each article's accessible name contains: `@handle · Nh ago [tweet text] [N replies, N reposts, N likes, N views]`.

Tweets marked with `StaticText "Ad"` are ads — skip them.

Timestamps to watch for: `1h`, `2h`, `6h`, `23h`, `Apr 17` (date = older than 24h, stop there).

**If snapshot returns a Gemini panel** (first line is `button "Close Gemini in Chrome"`), the GLIC flags failed to suppress it. In that case, fall back to screenshots — see Step 3b.

### Step 3b — Screenshot fallback (if Gemini hijacked the snapshot)

Take viewport screenshots instead. Twitter is always on the left; Gemini (if present) is on the right side panel and does not obscure the feed.

```bash
agent-browser screenshot /tmp/twitter_feed_1.png
```

Read each screenshot image to extract post content visually.

### Step 4 — Scroll and collect more posts

After reading the first viewport, scroll down and collect more posts. **Do not chain scroll + screenshot in a single `&&` command** — the agent-browser daemon needs a moment between commands or it returns `os error 35` (resource busy).

Run each command separately:
```bash
agent-browser scroll down 800
agent-browser screenshot /tmp/twitter_feed_2.png
agent-browser scroll down 800
agent-browser screenshot /tmp/twitter_feed_3.png
# ... continue until timestamps exceed --hours window
```

Stop when you see posts older than the requested window (`--hours`, default 24h).

### Step 5 — Expand truncated posts (optional)

If a tweet has `button "Show more"`, click it to reveal the full text:
```bash
agent-browser click @eNN   # ref from snapshot
```

### Step 6 — Close the browser

Always close when done:
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

- **Gemini side panel**: Chrome's built-in Gemini feature auto-opens on scroll even with `--disable-features=GLIC,GlicBootstrapping`. If it opens mid-session, switch from `snapshot` to `screenshot`. See [references/chrome-quirks.md](references/chrome-quirks.md).
- **Daemon busy errors** (`os error 35`): Do not chain `scroll && screenshot`. Run each as a separate command.
- **Chrome for Testing**: Do not omit `--executable-path`. Without it, agent-browser uses Chrome for Testing which has no saved sessions.
- **Auth state save/load**: Saving state with `agent-browser state save` does not reliably preserve Twitter cookies. Use `--profile Default` instead.

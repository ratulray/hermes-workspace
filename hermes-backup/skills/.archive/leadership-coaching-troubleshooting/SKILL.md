---
name: leadership-coaching-troubleshooting
description: Common failure modes and resolutions for the leadership-coaching skill — hermes send errors, last30days.py failures, async cron answer-collection gaps.
category: productivity
---

# Leadership Coaching — Troubleshooting

Common failure modes and their resolutions for the leadership-coaching skill.

---

## hermes send: "python-telegram-bot not installed"

**Symptom:** `hermes send --to "telegram:Ratul Ray"` fails with `python-telegram-bot not installed. Run: pip install python-telegram-bot`

**Root cause:** `hermes send` lazy-loads `python-telegram-bot`. The venv Python may not have pip, or the package was never installed into the venv's site-packages.

**Resolution (in order of likelihood):**

```bash
# Try system Python's pip first
/usr/bin/python3 -m pip install python-telegram-bot

# If that succeeds but hermes still fails, install into the venv
/usr/bin/python3 -m pip install --upgrade --target=/Users/ratul/.hermes/hermes-agent/venv/lib/python3.11/site-packages python-telegram-bot

# Verify it loads
hermes send --to "telegram:Ratul Ray" "test"
```

**Prevention:** The venv is built without pip by default. The first successful `hermes send` to Telegram auto-installs the dependency. Running `hermes send --list telegram` before the session is the cheapest trigger. If the session fires and the send fails, re-run the install above and then retry — the install is idempotent.

---

## last30days.py returns no usable results

**Symptom:** Script outputs instructions ("Web Claude will search the web") rather than findings, or returns 0 items.

**Root cause:** No `OPENAI_API_KEY` (Reddit) and no `XAI_API_KEY` (X). Script is working correctly — it has no data to work with.

**Resolution:** Fall back immediately. Do not retry, do not stall. Questions are grounded in the Maxwell tip principles themselves — the research supplements but never drives the session. Use the tip's core principle + own leadership knowledge + any direct WebSearch hits.

---

## Session fires but answers never arrive

**Symptom:** Questions sent, session stub saved, but Ratul never replies and no feedback is delivered.

**Resolution:** This is expected behavior for async cron. The session file at `/Users/ratul/Documents/leadership_conversation/{YYYY-MM-DD}.md` is the state artifact. When Ratul replies in a later cron tick, the next session can pick up the thread. The tracking file (`/tmp/leadership-coaching-last-topics.txt`) is already updated so there is no double-selection risk on retry.

---

## Cron job deliver: local vs. telegram

The cron is configured `deliver: local` — output saves to a file but nothing is sent to Telegram automatically. The session itself must use `hermes send` for all Telegram delivery. This is the correct and intended setup; no fix needed. Just remember that `sessions_send` and `send_message` tools are not available in cron context — only `hermes send`.

---

## Tip ID collision / double-selection

**Symptom:** Same tip selected twice across consecutive sessions.

**Prevention:** Always read `/tmp/leadership-coaching-last-topics.txt` before tip selection and append newly selected tip IDs immediately — before sending any questions. The skill protocol specifies: update tracking BEFORE sending Q1. This ensures that even if the job crashes mid-send, the tip is already marked used and won't be double-selected on retry.

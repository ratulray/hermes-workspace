# Leadership Coaching — Troubleshooting

Common failure modes and their resolutions. Load when something breaks during session setup or delivery.

---

## hermes send: "python-telegram-bot not installed"

**Symptom:** `hermes send --to "telegram:Ratul Ray"` fails with `python-telegram-bot not installed. Run: pip install python-telegram-bot`

**Root cause:** `hermes send` lazy-loads `python-telegram-bot`. The venv Python may not have pip, or the package was never installed into the venv's site-packages.

**Resolution (in order of likelihood):**

```bash
# Try system Python's pip first
/usr/bin/python3 -m pip install python-telegram-bot

# If that succeeds but hermes still fails, install into the venv directly
/usr/bin/python3 -m pip install --upgrade \
  --target=/Users/ratul/.hermes/hermes-agent/venv/lib/python3.11/site-packages \
  python-telegram-bot

# Verify
hermes send --to "telegram:Ratul Ray" "test"
```

**Prevention:** The venv is built without pip by default. Running `hermes send --list telegram` before the session is the cheapest trigger that exercises the dependency. The install is idempotent — re-running is safe.

---

## last30days.py returns no usable results

**Symptom:** Script outputs instructions ("Web Claude will search the web") rather than findings, or returns 0 items despite waiting.

**Root cause:** No `OPENAI_API_KEY` (Reddit) and no `XAI_API_KEY` (X). Script is working correctly — it has no live data sources.

**Resolution:** Fall back immediately. Do not retry, do not stall.

- Fall back = Maxwell tip core principle + own leadership knowledge + any direct WebSearch hits
- Questions are grounded in the Maxwell tip principles themselves — research supplements but never drives the session
- This is a permanent, expected failure mode. Never let thin research block question delivery.

---

## Cron fires but hermes send fails silently or times out

**Symptom:** Session selects tips, sends nothing to Telegram, no error visible in output.

**Check:** Is `python-telegram-bot` installed in the venv? (See above)

**Check:** Is the target name correct? Run `hermes send --list telegram` to confirm exact format.

---

## Same tip selected twice across sessions

**Symptom:** Tracking file `/tmp/leadership-coaching-last-topics.txt` not updated before sending — crash mid-session causes retry to re-select the same tips.

**Prevention:** Always append tip IDs to tracking file BEFORE sending Q1. The file is the lock that prevents double-selection. Update it at tip selection time, not at session end.

---

## Session fires but answers never arrive / no feedback delivered

**Symptom:** Questions sent, session stub saved, but Ratul never replies.

**This is expected behavior for async cron.** The session file at `/Users/ratul/Documents/leadership_conversation/{YYYY-MM-DD}.md` is the state artifact. When Ratul replies in a later cron tick, the next session can pick up the thread or a new coaching cycle begins. The tracking file is already updated so there is no double-selection risk on retry.

---

## Cron job deliver: local vs. telegram

The cron is configured `deliver: local` — output saves to a file but nothing is sent to Telegram automatically. This is the correct setup. The session itself must use `hermes send` for all Telegram delivery.

- `sessions_send` tool — NOT available in cron context
- `send_message` tool — NOT available in cron context  
- `hermes send` CLI — works in any non-interactive context (cron, pipe, subprocess)

No fix needed. Just know the right tool for the job.

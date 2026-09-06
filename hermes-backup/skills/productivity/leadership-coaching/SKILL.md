---
name: leadership-coaching
description: Weekly leadership coaching practice for Ratul Ray — select tips, research topics, run reflective interviews, and deliver honest feedback. Uses John C. Maxwell's "Winning With People" tip collection as the source material.
argument-hint: Run the weekly Friday leadership coaching session | leadership coaching session this week | coach me on leadership
allowed-tools: Read, Write, Bash, WebSearch, terminal
# Note: `terminal` is the correct tool name (Bash is the underlying mechanism; hermes send is a Bash subcommand).
note on delivery: Use `hermes send --to "telegram:<TargetName>"` — NOT `sessions_send` (unavailable in cron), NOT `send_message`. The `hermes send` CLI routes through the gateway's bot tokens and works in any non-interactive context. Target names are discovered via `hermes send --list telegram`.
trigger-conditions:
  - user asks for leadership coaching, leadership advice, leadership tips
  - Friday evening arrives (scheduled cron job fires)
  - user says "coach me" or "be my leadership coach"
user-invocable: true
metadata:
  practice_type: reflective-coaching
  source_material: John C. Maxwell / Winning With People
  frequency: weekly (Friday 9pm PT)
  delivery: Telegram
tags: [leadership, coaching, reflection, maxwell]
related_skills: []
sources: []
created: 2026-05-21
updated: 2026-05-21
---

# Leadership Coaching — Weekly Practice

Delivers a structured, research-backed coaching session every Friday at 9pm PT. Each session:
1. Selects 2 fresh tips from the Maxwell collection (avoids repeating recent topics)
2. Runs online research to gather modern perspectives and frameworks
3. Sends Ratul open-ended interview questions via Telegram
4. Receives Ratul's answers and delivers brutally honest feedback

---

## Session Structure

### Phase 1 — Tip Selection
- Read `/tmp/leadership-coaching-last-topics.txt` to avoid repeating recent tips
- Scan `/Users/ratul/Documents/leadership_notes/tips/winning-with-people/`
- Pick exactly **2 tips** that are thematically distinct from each other and from recent sessions
- Read both tip `.md` files in full to extract the core principle

Research goals per tip:
- What do great leaders do differently on this dimension?
- Common failure modes for this leadership quality
- Practical frameworks or mental models
- Signals of genuine mastery vs. performed leadership

**Research execution**: Locate the script first via `find /Users/ratul/.hermes ~ -maxdepth 6 -name "last30days.py" 2>/dev/null` or `which last30days`. The skill docs have historically referenced `./scripts/last30days.py` relative to the skill dir — this path has not been reliable across sessions.

Once found, invoke: `python3 /path/to/last30days.py "$ARGUMENTS" --emit=compact 2>&1`
- The script accepts `--quick` or `--deep` as direct positional flags. There is NO `--depth=` prefix. Using `--depth=quick` causes an "unrecognized arguments" error and the flag is silently ignored — it does not fail visibly. Always use `--quick` directly without the `depth=` prefix.

**Note on API keys**: last30days needs `OPENAI_API_KEY` for Reddit and `XAI_API_KEY` for X. Without them it runs in web-only mode and may return limited results. Do not let thin research block the session — fall back to the Maxwell tip's core principle and your own leadership knowledge. The questions matter more than the research.

### Phase 3 — Interview Delivery (Telegram / Cron)

**For Telegram cron sessions:**

The cron fires once per execution and cannot wait between questions. However, this does NOT mean all questions must go out in the same run. **A better pattern is one question per run**, preserving coaching quality:

1. **First cron tick**: Select tips → research → send Q1 via `hermes send` → save session stub with Q1 recorded and Q2 in stub as "pending" → update `/tmp/leadership-coaching-last-topics.txt`
2. **Second cron tick** (after Ratul replies): Send Q2 via `hermes send` → save session stub with Q2 now sent
3. **Third cron tick** (after both answers): Deliver full feedback via `hermes send`

> ⚠️ **CRITICAL**: The `deliver: local` setting on the cron job means the session output is saved to a file but no Telegram message is auto-sent. The session must use `hermes send` for ALL message delivery. This is the same protocol as manual in-chat sessions — the cron context just requires explicit `hermes send` calls.

**Protocol for each cron tick:**
- Send message(s) via `hermes send --to "telegram:Ratul Ray"`
- Update session file after each send
- Do NOT use `sessions_send` or `send_message` tool
- Use `hermes send --list telegram` to confirm target name

**On sending Q1 and Q2 in the same tick**: The "never both in same tick" rule is calibrated for manual in-chat sessions where Ratul is actively engaged and the gap between questions is where reflection happens. For async Telegram cron, sending both in one tick is often the right call — the gap between cron ticks (potentially days) provides natural reflection time, and Ratul can answer both questions in a single reply. Use judgment: if the next cron tick won't fire until after you expect a reply, sending both together is acceptable. The multi-tick protocol remains the ideal, but don't let perfect be the enemy of good.

After all questions sent, send a follow-up message: *"Take your time with these — answer whenever feels right. I'll deliver feedback once I have both."*

**Format rules (Telegram cron sessions):**

When Ratul initiates a coaching session in-chat ("Let's start a new session" or similar):

1. **Load the obsidian-markdown skill** — the session output will be saved as an Obsidian note.
2. **State the session is starting** — tell Ratul you'll ask questions one at a time, record answers, and deliver feedback at the end.
3. **Ask each question using the full original text** — pull the exact question text from the session plan (see `references/session-plan-template.md`), not a shortened version. If the session plan contains multiple questions, ask them one by one in order.
4. **Record each answer** — note it alongside the question. Do not give feedback during the interview phase.
5. **After all questions answered**, deliver the full feedback report in-chat.
6. **Save to Obsidian** — write the complete session file using the obsidian-markdown skill (frontmatter, callouts per feedback thread, quote callout for bottom line). Filename: `{YYYY-MM-DD}.md` in the session directory.
7. **Update topic tracking** — append the two tip IDs to `/tmp/leadership-coaching-last-topics.txt`.

**Format rules (Telegram cron sessions):**
- Tips stay anonymous. Never reveal which Maxwell tip a question comes from, or even that it came from a tip. Questions stand on their own.
- Send Q1 in the first cron tick. Do NOT send Q2 in the same tick — the multi-tick protocol means Q2 waits until Ratul replies. Sending both at once breaks the reflection rhythm.
- After Q1 sent, update the session stub file immediately (Q1 recorded, Q2 pending). This preserves state if the process crashes.
- When Ratul's reply arrives (next cron tick), send Q2. After both sent, add a follow-up: *"Take your time with these — answer whenever feels right. I'll deliver feedback once I have both."*
- Never give feedback after individual answers during the interview phase. Collect all answers first, then deliver full feedback.
- If Ratul asks "is this from one of the tips?", acknowledge but don't confirm which one.

> ⚠️ **Why multi-tick matters**: Sending Q1 and Q2 together turns the session into a questionnaire, not a coaching conversation. The gap between question and reply is where reflection happens. Protecting that gap is part of the coaching act itself.

**Format rules (manual in-chat sessions):**
- Same as above except: ask one question, wait for answer, record answer, then ask next.
- Never give feedback after individual answers during the interview phase. Collect all answers first, then deliver full feedback.
- If Ratul asks "is this from one of the tips?", acknowledge but don't confirm which one.

**On question sequencing**: Start with questions likely to produce revealing answers — even if that means abandoning the planned order. The goal is reflective discomfort, not coverage. If an answer opens a thread that matters more than the next planned question, chase that thread. A session that answered 4 questions deeply is worth more than one that rattled through 8 superficially.

**On pushing for specifics**: When Ratul gives a generic answer ("career development takes a back seat"), push immediately for one concrete example — a specific conversation not had, a specific person who paid the price. Generic patterns are defense. Specific moments are where the real work happens.

**On mid-session synthesis**: If a pattern has clearly emerged by Q3 or Q4, pause and name it before continuing. Example: "Everything you've described — skip-leveling, no career conversations, no follow-up — has the same root cause. Want to sit with that before the next question?" This is more valuable than mechanical question delivery.

**What to do when a planned question gets abandoned**: If you switch to a different question than planned because the conversation went somewhere more important, make a note of the abandoned question internally. Do not mention it to Ratul.

**Research failure protocol**: last30days.py reliably fails in web-only mode — it outputs instructions ("Claude will search the web") rather than actual data. This is NOT a signal to retry or escalate. It is a known, permanent failure mode. Protocol:

1. Run the script as normal (do not pre-check for keys)
2. If output says "Web Claude will search the web" or returns no actual findings within 60s, immediately fall back
3. Fall back = Maxwell tip core principle + own leadership knowledge + any relevant Hacker News/WebSearch hits you can pull directly
4. Send questions. Never delay questions to wait for better research.
   This matters when you need research on 2 tips before sending questions.

### Phase 4 — Feedback Delivery (Manual In-Chat)

After all questions answered in-chat, deliver the full feedback report. Structure:

1. **Per-question assessment** — grade the answer against what great leadership looks like on that dimension. Name the gap between intent and impact. Be specific: quote what he said, then tell him what it reveals.
2. **Through-line** — identify the single pattern connecting all answers. This is the most valuable synthesis.
3. **One concrete action** — exactly one thing he can do in the next 7 days. Not a principle, not a mindset shift — a specific action with a specific person or meeting attached.

**After feedback**: save the complete session file, then update the tracking file.

### Phase 4 — Session File Lifecycle (Cron Mode)

In cron mode, answers arrive asynchronously via Telegram replies. The session file has three states:

1. **Stub save (first cron tick — Q1 sent):** Write the session file with Q1 recorded and Q2 as "pending". Mark status clearly: questions sent, answers pending. This preserves state if the process crashes mid-send.
2. **Q2 sent (second cron tick):** Update session file — mark Q2 as sent. Answers may or may not have arrived.
3. **Full save (final cron tick):** When answers arrive, update session file with actual answers, deliver feedback via `hermes send`, then mark complete.

**Tracking file update timing**: Update `/tmp/leadership-coaching-last-topics.txt` at stub-save time (before sending Q1), not at full-save time.

---

## Tips for Great Interview Questions

The goal is **reflective discomfort** — not making him feel bad, but making him think. Good coaching questions:
- Reveal the gap between intent and impact
- Surface the story he tells himself vs. what actually happened
- Push on assumed tradeoffs (e.g., "patience vs. velocity") with concrete scenarios

**Anti-patterns to avoid**:
- Questions Ratul can answer with a rehearsed leadership talking point
- Generic questions that could apply to any manager at any company
- Questions where the "right answer" is obvious before he even thinks

---

## Tracking & Continuity

**Topic tracking file**: `/tmp/leadership-coaching-last-topics.txt`
- **Update BEFORE sending questions** — if the job crashes mid-send, the topic is already marked as used and won't be double-selected on retry.
- Read this file at session start to avoid repeating topics.
- Append the two tip IDs immediately after tip selection, before sending anything.

**Session history**: Consider a running log at `/Users/ratul/Documents/leadership_notes/coaching-sessions/` with one file per session (date as filename) capturing: tips selected, research notes, questions asked, and overall assessment.

---

## Related: Daily Leadership Tip (lightweight variant)

There is also a **lightweight daily tip** skill at `openclaw-imports/leadership-advice` (now archived — content below). It delivers one random leadership tip per evening at 10 PM PT via Telegram, without the full coaching interview cycle. It uses the same Maxwell tip source as this skill.

**If the user wants quick daily tips** instead of a full coaching session, use this pattern:

1. Pick a random tip from `/Users/ratul/Documents/leadership_notes/tips/**/*.md`
2. Avoid repeating any tip delivered in the last 30 days (check `~/.openclaw/skills/leadership-advice/state.json`)
3. Deliver in the format:
   ```
   > **Leadership Tip**
   > {tip text}
   > — *{title} · {author}*
   >
   > _(Ask me anything about this)_
   ```
4. Track delivery in state file (append to `delivered` array, prune entries > 30 days old)

**State file** (`~/.openclaw/skills/leadership-advice/state.json`):
```json
{
  "delivered": [
    { "id": "catalyst-001", "date": "2026-05-03" }
  ]
}
```

**On follow-up questions**: Load wiki pages from `/Users/ratul/Documents/leadership_notes/wiki/**` using the `wiki_refs` from the tip's frontmatter.

---

## ⚠️ Pitfalls

### Telegram Delivery in Cron Context
The cron job is configured `deliver: local` (saves output to file, no external send). The session itself must drive Telegram delivery using `hermes send`.

**Working approach (cron/Telegram):**
```bash
# Discover target names
hermes send --list telegram
# Send Q1 only in first cron tick — Q2 waits for Ratul's reply
hermes send --to "telegram:Ratul Ray" "Q1 text"
# Session stub saved to /Users/ratul/Documents/leadership_conversation/{date}.md
# On next cron tick (after Ratul replies), send Q2:
hermes send --to "telegram:Ratul Ray" "Q2 text"
# After both sent, add follow-up:
hermes send --to "telegram:Ratul Ray" "Take your time — I'll deliver feedback once I have both answers."
```
- `sessions_send` is NOT available in cron context — do not use it
- `send_message` tool is NOT available — do not use it
- `hermes send` works in any non-interactive context (cron, pipe, subprocess)
- Target name format: `"telegram:<Name>"` where `<Name>` is the contact's display name as shown in `hermes send --list telegram`
- **Never send Q1 and Q2 in the same cron tick** — the gap between them is where reflection lives

### Research returning near-zero results (402 on Reddit, X not authenticated): Fall back to hackernews + web search. Do NOT retry the failing source. Quality of research matters less than quality of questions — if research is thin, fall back to known frameworks and your own knowledge of leadership.
- **Asking questions that are too soft**: If the question doesn't feel like it could produce an uncomfortable truth, it needs to be harder.
- **Feedback that is too kind**: Brutal honesty only helps if it's actually brutal. "This is good" should mean something.
- **Repeating tips**: Always check `/tmp/leadership-coaching-last-topics.txt` first.

---

## Supporting Files

- `references/session-plan-template.md` — blank template for preparing future sessions (fill in tips, research, questions, feedback before each session)
- `references/sample-session.md` — May 22 inaugural session (full arc: tip selection → research → questions → feedback, 7 questions, identity-protection loop named)
- `references/question-bank.md` — bank of coaching questions organized by Maxwell theme, with session-derived questions from May 22
- `references/session-2026-05-29.md` — May 29 session (proportionality + learning board), documents the delivery gap with `deliver: local`
- `references/session-2026-06-07.md` — June 7 cron session (confrontation/action plans + relational deposits), 6 questions sent via `hermes send`, Q1-Q2 connect to follow-through gap, Q3-Q6 connect to urgency ratchet / neglect pattern
- `references/session-2026-06-07-manual.md` — June 7 manual in-chat session (same questions answered in-chat); canonical example of the manual workflow: direct questions → inline answers → feedback → Obsidian save
- `references/session-2026-07-03.md` — Jul 3 session (celebrating peers' success + uncalculating giving), 2 questions sent via `hermes send`, tips 082 + 090, research failed gracefully via fallback protocol
- `references/session-2026-07-10.md` — Jul 10 session (usefulness orientation + real friendship / Henry Ford test), tips 030 + 095, last30days.py path not found, fell back to Maxwell + own knowledge, 2 questions sent, answers pending
- `references/session-2026-07-17.md` — Jul 17 session (consistency + earned trust / genuine allies vs. strategic contacts), tips 055 + 070, 2 questions sent via `hermes send`, answers pending
- `references/troubleshooting.md` — common failure modes: hermes send pip error, last30days zero-results fallback, deliver:local vs telegram, tracking file updates

| 2026-08-07 | 040, 090 | Genuine curiosity + generous giving | Seen vs. interrogated, generosity ledger |
| 2026-08-14 | 103, 099 | Learnable relational skills + complementary strengths | Partnership complementarity; effective vs. stalled collaborations |

*Last updated: 2026-08-14*

---

## Session Reference Log

Use this to reconstruct what was covered in each session without re-reading full files. Full session files live at `/Users/ratul/Documents/leadership_conversation/{YYYY-MM-DD}.md`.

| Date | Tips | Theme | Questions |
|------|------|-------|-----------|
| 2026-05-21 | 104, 080 | Inner work + patience | Inaugural session; skip-leveling, career debt, identity loop |
| 2026-06-07 | 050, 073 | Confrontation/action + relational deposits | Follow-through gap, urgency ratchet, neglect pattern |
| 2026-06-26 | 069, 070 | Inner circle quality + genuine allies | Peer network, wound accumulation |
| 2026-07-03 | 082, 090 | Joy at others' success + uncalculating giving | Celebrating peers, generosity ledger |
| 2026-07-10 | 030, 095 | Usefulness orientation + real friendship | Henry Ford test, seen vs. interrogated |
| 2026-07-17 | 055, 070 | Consistency + earned trust | Integrity track record, genuine vs. strategic contacts |
| 2026-07-24 | 104, 082 | Self-awareness (reprise) + joy at success | Inner work, celebrating without stealing |
| 2026-07-31 | 065, 085 | Self-security + stealing thunder | Vulnerability safety, attribution without self-promotion |
| 2026-08-07 | 040, 090 | Genuine curiosity + generous giving | Seen vs. interrogated, generosity ledger |
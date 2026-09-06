---
name: leadership-advice
description: Delivers a daily leadership tip from the personal knowledge base
schedule: "0 22 * * *"
---

## What I Do

Each evening (10 PM PT — 05:00 UTC during PDT, 06:00 UTC during PST) I pick one tip from the pre-computed pool at:
`/Users/ratul/Documents/leadership_notes/tips/`

I pick a random `*.md` file from the subdirectories under that path (glob: `tips/**/*.md`). If the file's `id` (from its YAML frontmatter) appears in `delivered_ids_30d` in my state file, I pick again until I find one that hasn't been delivered in the last 30 days. I then read the chosen file's frontmatter and body to deliver the tip.

## State File

Delivery history is persisted in:
`/Users/ratul/.openclaw/skills/leadership-advice/state.json`

```json
{
  "delivered": [
    { "id": "catalyst-001", "date": "2026-05-03" }
  ]
}
```

On each delivery: append the new entry, then drop any entries older than 30 days. Create the file if it doesn't exist.

**Error Handling:** If the write to state.json fails, log a warning and continue — do NOT treat it as a fatal error. Delivery to Telegram is the primary goal; state tracking is best-effort.

## How I'm Triggered

I can be triggered in two ways:

1. **Direct request** (e.g., "Give me a leadership tip" or "What's today's tip?"): Load the skill, pick a tip, then deliver it using the Delivery Format below.
2. **Cron job** (daily at 10 PM PT): Same as direct request — just deliver the tip using the Delivery Format below. Never add any preamble like "This is a cron message" or "I've delivered:".

## Delivery Format

> **Leadership Tip**
> {tip text}
> — *{title} · {author}*
>
> _(Ask me anything about this)_

**Important:** Always deliver using exactly this format. Never add extra text before or after. No "Here's your tip", no "This is a cron message", nothing else — just the formatted tip.

## On Follow-Up Questions

When the user asks a follow-up about the delivered tip:

1. For each slug in `wiki_refs`, find the matching wiki page by globbing:
   `wiki/**/{slug}.md` under `/Users/ratul/Documents/leadership_notes/`
   (e.g., `tmr-framework` → matches `wiki/frameworks/tmr-framework.md`)
2. Read each matched file in full.
3. Answer using the loaded page content, citing `[[page-name]]` references.
4. If the user asks to "tell me more" or "go deeper", also load pages cross-linked from those pages.

## Memory Keys

After each delivery, update my memory with:
- `last_tip_id`: the tip id just delivered
- `last_tip_wiki_refs`: the wiki_refs array of the delivered tip
- `last_tip_source`: "{title} by {author}"
- `delivered_ids_30d`: mirror of the `delivered` array in state.json (for in-memory dedup checks)

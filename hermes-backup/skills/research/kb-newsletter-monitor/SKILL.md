---
name: kb-newsletter-monitor
description: Run the Monday KB newsletter monitor and deep dives.
metadata:
  hermes:
    tags: [newsletter, cron, agent-roadmap, evals]
---

# KB Newsletter Monitor (cron 70bb168c25de)

Monitors `~/Documents/agent-roadmap/newsletters/` (symlink → `~/.openclaw/workspace-jim/ai-knowledge-base/newsletters/`) for new entries and surfaces relevant ones to Ratul.

## Pipeline
1. `ls -lt` the newsletters dir. New = filename not in `~/Documents/agent-roadmap/kb-monitor/last-seen.txt` (one filename per line).
2. Read each new file fully. Delegate to parallel `delegate_task` children (3–4 files each) to protect context — ask each child for a 2–3 sentence factual summary plus a high/medium/low relevance rating with one concrete reason tied to a specific idea in the file.
3. Relevance lens: enterprise multi-agent conversational AI — orchestration, quality/consistency, observability, complex workflows, HITL, agent evaluation, dev experience. Surface plausible connections, not just exact matches.
4. Write the `[KB Signal]` blocks (Topic / Relevance to your team / "Want me to go deeper? (yes/no)") into the **final response** — see delivery note below.
5. Append processed filenames to `last-seen.txt` **after** reading, so a mid-run failure doesn't skip files.

## Delivery: no `send_message` in cron sessions
`send_message` is NOT exposed in the cron session — `tool_search` for it returns nothing, and hosted connectors are not set up. The cron harness delivers the final assistant response to Telegram automatically. So: **put every signal inline in the final response**, one `---`-delimited block per entry, and do not attempt to send separately.

## Picking up YES replies
Ratul's replies arrive in the Telegram chat session, not in the cron session. To detect them on a later run, use `session_search` with `role_filter: "user"` over recent user sessions — the cron sessions themselves only contain the job prompt (they match on "KB Signal" / "go deeper" text and are noise). Filter them out by checking `source`/session id prefix `cron_`.

## Deep-dive step (on YES)
- `skill_view(name='last30days')` and research the topic (Reddit HTTP 402 → fall back to `--search=hackernews,web`; X returns 0 unauthenticated; needs Python 3.12+).
- Write `~/Documents/agent-roadmap/kb-deep-dives/{date}-{slug}.md` — summary, 3–5 roadmap ideas with implementation notes, links.
- Use Obsidian Flavored Markdown (see the `obsidian-markdown` skill).

## Pitfalls
- `last-seen.txt` gets truncated by some past runs — always **union** the new filenames into the existing file, never overwrite with only this run's batch, or old entries re-surface as new.
- Existing deep dives in `kb-deep-dives/` may already cover a topic (e.g. `2026-07-28-coding-agent-harness-engineering.md`, `2026-06-22-glm-5-2-open-agents.md`). Check before proposing a dive and say what is new vs. already covered.
- Interconnects digests are often captured from emails truncated at ~1500 chars — specifics (model names, licenses) may simply be absent; don't fill the gap from memory.
